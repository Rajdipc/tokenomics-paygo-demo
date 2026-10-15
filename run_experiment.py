"""Token Bill of Materials (TBOM) experiment runner for the Cymbal Insurance Claims Agent.

This script imports the agent, tools, and TBOM ledger from ``cymbal_claims_agent/``
and runs the same synthetic insurance claims through five progressive designs
(``R0`` -> ``R1`` -> ``R2`` -> ``R3`` -> ``R5``) plus the fault-injection loop-guard
comparison (``R4U`` vs ``R4G``), writing itemized telemetry to ``results/<run_tag>/``:

    pip install -r requirements.txt
    source .env
    python run_experiment.py --runs R0 R1 R2 R3 R5 --n 50 --trace
    python run_experiment.py --runs R4U R4G --n 40 --trace

To deploy the production R5 Google ADK agent (``cymbal_claims_agent``) to Cloud Run
or Gemini Platform Agent Runtime (Vertex AI Agent Engine), see ``deploy/`` and ``README.md``.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import os
import pathlib
import re
import sys
import threading

from cymbal_claims_agent import (  # noqa: F401 - re-exported for tests and callers
    BASELINE_SYSTEM,
    DECOYS,
    EXPLICIT_CACHE_MODELS,
    FLASH,
    FLASH_LITE,
    FRONTIER,
    GET_HISTORY,
    GET_POLICY,
    LINE_ITEMS,
    OPTIMIZED_SYSTEM,
    PRICES,
    R0,
    R1,
    R2,
    R3,
    R4G,
    R4U,
    R5,
    REVIEWER_SYSTEM,
    RUNS,
    SCREEN,
    STRICT_LINE,
    SUBMIT,
    TIER,
    TRIAGE_SCHEMA,
    TRIAGE_SYSTEM,
    Agent,
    Conversation,
    Gemini,
    Jsonl,
    RunConfig,
    Store,
    Tools,
    allocate,
    chars_of,
    claim_text,
    decl,
    handbook_block,
    read_csv,
    schema_chars,
    token_cost,
    toolset,
)

HERE = pathlib.Path(__file__).resolve().parent
DATA = HERE / "data"


def setup_tracer():
    """Optional: send spans to Cloud Trace (--trace), billed to GOOGLE_CLOUD_PROJECT."""
    import google.auth
    from google.cloud.trace_v2 import TraceServiceClient
    from opentelemetry import trace
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    project = os.environ["GOOGLE_CLOUD_PROJECT"]
    creds, _ = google.auth.default(quota_project_id=project)
    exporter = CloudTraceSpanExporter(project_id=project, client=TraceServiceClient(credentials=creds))
    provider = TracerProvider(resource=Resource.create({"service.name": "tbom-claims-demo"}))
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return trace.get_tracer("tbom"), provider


def main(argv=None, gemini=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs", nargs="+", default=["R0", "R1", "R2", "R3", "R5"], choices=list(RUNS))
    ap.add_argument("--n", type=int, default=50, help="claims per run (the same claims for every run)")
    ap.add_argument("--workers", type=int, default=4, help="claims processed in parallel")
    ap.add_argument("--max-usd", type=float, default=75.0, help="stop when the list-price estimate reaches this")
    ap.add_argument("--run-tag", default=os.environ.get("TBOM_RUN_TAG") or f"exp-{dt.date.today()}")
    ap.add_argument("--trace", action="store_true", help="also send spans to Cloud Trace")
    args = ap.parse_args(argv)
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,62}", args.run_tag):
        sys.exit("--run-tag: lowercase letters, digits, '-' or '_' only (it becomes a billing label)")

    store = Store()
    gemini = gemini or Gemini()
    tracer, provider = setup_tracer() if args.trace else (None, None)
    out = HERE / "results" / args.run_tag
    calls, claims_out, runs_out = Jsonl(out / "calls.jsonl"), Jsonl(out / "claims.jsonl"), Jsonl(out / "runs.jsonl")
    claims = store.claims[: args.n]
    spent, lock = 0.0, threading.Lock()
    print(f"run_tag={args.run_tag}  claims={len(claims)}  runs={args.runs}  ->  {out}")

    for run_id in args.runs:
        if spent >= args.max_usd:
            print(f"skipping {run_id}: --max-usd reached")
            continue
        cfg = RUNS[run_id]
        agent = Agent(cfg, store, gemini, args.run_tag, calls, claims_out, tracer)
        started = dt.datetime.now(dt.timezone.utc)
        agent.create_caches()
        batches = (
            [claims[i : i + 3] for i in range(0, len(claims), 3)]
            if cfg.session == "queue"
            else [[c] for c in claims]
        )
        rows: list[dict] = []
        try:
            with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
                futures = [pool.submit(agent.process, b) for b in batches]
                for fut in cf.as_completed(futures):
                    batch_rows = fut.result()
                    rows += batch_rows
                    with lock:
                        spent += sum(r["cost_usd"] for r in batch_rows)
                    if spent >= args.max_usd:
                        for f in futures:
                            f.cancel()
                        break
        finally:
            storage, creation = agent.delete_caches()
        spent += storage + creation
        runs_out.write({
            "run_tag": args.run_tag,
            "run_id": run_id,
            "title": cfg.title,
            "n_claims": len(rows),
            "started_at": started.isoformat(),
            "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "cache_storage_usd": round(storage, 6),
            "cache_creation_usd": round(creation, 6),
            "simulated": gemini.simulated,
        })
        n = len(rows) or 1
        ok = sum(r["correct"] for r in rows)
        llm = sum(r["cost_usd"] for r in rows) + storage + creation
        prompt = sum(r["prompt_tokens"] for r in rows)
        print(
            f"{run_id:4s} {cfg.title[:40]:40s} claims={len(rows):3d} accuracy={ok / n:6.1%} "
            f"tokens/claim={(prompt + sum(r['output_tokens'] + r['thoughts_tokens'] for r in rows)) / n:9,.0f} "
            f"cached={sum(r['cached_tokens'] for r in rows) / max(prompt, 1):4.0%} "
            f"$/claim={llm / n:.4f} errors={sum(1 for r in rows if r['error'])}"
        )
    if provider:
        provider.shutdown()
    print(f"List-price estimate for this invocation: ${spent:,.2f}.  Next: upload {out} to BigQuery (RUNBOOK step 6).")


if __name__ == "__main__":
    main()
