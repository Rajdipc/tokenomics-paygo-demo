"""Workload-shaped test for the token-burn alert (follow-up to the R4 failure scenario).

Question: does a fleet-wide token-rate alert tell a busy healthy run apart from a quieter looping one?

The R4 test held arrival rate constant and injected one failure pattern. This grid varies two
things independently, on the same unguarded agent design (R4U by default):

  * arrival rate: claims per minute, open loop (claims arrive on a clock, not when a worker frees up)
  * faulty-tool fraction: share of claims whose fraud screening times out

Every --sample-seconds it records the signals an alert could watch:

  tokens/min                        what the R4 alert watches (rolling 60 s)
  admitted/min, completed/min       how much work came in and how much finished
  in-flight claims, oldest age      how long the oldest unfinished claim has been running
  tokens and model calls per admitted claim (rolling 3 min)
  max model calls made by any single claim in flight or finished in the last minute

Run, then analyse:

    source .env
    pip install google-cloud-monitoring matplotlib     # optional: --emit-metrics and the chart
    python workload_grid.py --rates 4 8 --fault-rates 0 0.05 0.2 --minutes 6 \\
        --run-tag grid-1113 --emit-metrics
    python workload_grid.py --analyze results/grid-1113 --cm-check

Output in results/<run_tag>/: calls.jsonl, claims.jsonl and runs.jsonl (same schema as
run_experiment.py, so they load into the same BigQuery tables), samples.jsonl (the time series),
grid_summary.md and grid_signals.png.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import dataclasses
import datetime as dt
import json
import os
import pathlib
import re
import sys
import threading
import time

from cymbal_claims_agent import RUNS, Agent, Gemini, Jsonl, Store

HERE = pathlib.Path(__file__).resolve().parent
SIGNALS = (
    "tokens_per_min",
    "admitted_per_min",
    "completed_per_min",
    "inflight",
    "oldest_inflight_age_s",
    "tokens_per_admitted_claim_3m",
    "calls_per_admitted_claim_3m",
    "max_calls_per_claim_1m",
)


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def pick_faulty(claims: list[dict], fraction: float) -> frozenset[str]:
    """Evenly spaced faulty claims, so 5% of 24 claims is exactly one claim, not 'maybe zero'."""
    eps = 1e-9
    return frozenset(
        c["claim_ref"]
        for i, c in enumerate(claims)
        if int((i + 1) * fraction + eps) > int(i * fraction + eps)
    )


class Tracker:
    """Live workload state for one grid cell: what an alert could see at any moment."""

    def __init__(self):
        self.lock = threading.Lock()
        self.t0 = time.monotonic()
        self.phase = "arrivals"
        self.admitted: list[float] = []
        self.completed: list[float] = []
        self.calls: list[tuple[float, int]] = []
        self.inflight: dict[str, float] = {}
        self.claim_calls: dict[str, int] = {}
        self.done_at: dict[str, float] = {}

    def admit(self, ref: str) -> None:
        with self.lock:
            now = time.monotonic()
            self.admitted.append(now)
            self.inflight[ref] = now

    def complete(self, ref: str) -> None:
        with self.lock:
            now = time.monotonic()
            self.completed.append(now)
            self.done_at[ref] = now
            self.inflight.pop(ref, None)

    def on_call(self, row: dict) -> None:
        tokens = int(row["prompt_tokens"]) + int(row["output_tokens"]) + int(row["thoughts_tokens"])
        with self.lock:
            self.calls.append((time.monotonic(), tokens))
            self.claim_calls[row["claim_ref"]] = self.claim_calls.get(row["claim_ref"], 0) + 1

    def snapshot(self) -> dict:
        with self.lock:
            now = time.monotonic()

            def count(xs, w):
                return sum(1 for x in xs if now - x <= w)

            tok60 = sum(t for x, t in self.calls if now - x <= 60)
            tok180 = sum(t for x, t in self.calls if now - x <= 180)
            calls180 = count([x for x, _ in self.calls], 180)
            adm180 = count(self.admitted, 180)
            recent = set(self.inflight) | {r for r, t in self.done_at.items() if now - t <= 60}
            return {
                "elapsed_s": round(now - self.t0, 1),
                "phase": self.phase,
                "tokens_per_min": tok60,
                "admitted_per_min": count(self.admitted, 60),
                "completed_per_min": count(self.completed, 60),
                "inflight": len(self.inflight),
                "oldest_inflight_age_s": round(max((now - a for a in self.inflight.values()), default=0.0), 1),
                "tokens_per_admitted_claim_3m": round(tok180 / adm180) if adm180 else None,
                "calls_per_admitted_claim_3m": round(calls180 / adm180, 2) if adm180 else None,
                "max_calls_per_claim_1m": max((self.claim_calls.get(r, 0) for r in recent), default=0),
            }


class TrackedCalls:
    """Writes the per-call ledger exactly like run_experiment.py and feeds the live tracker."""

    def __init__(self, sink: Jsonl):
        self.sink, self.tracker = sink, None

    def write(self, row: dict) -> None:
        if self.tracker is not None:
            self.tracker.on_call(row)
        self.sink.write(row)


class MetricEmitter:
    """Optional: writes the workload signals to Cloud Monitoring as custom gauge metrics."""

    def __init__(self, project: str, run_tag: str):
        import google.auth
        from google.cloud import monitoring_v3

        creds, _ = google.auth.default(quota_project_id=project)
        self.mon, self.project, self.run_tag = monitoring_v3, project, run_tag
        self.client = monitoring_v3.MetricServiceClient(credentials=creds)
        self.warned = False

    def emit(self, snap: dict, cell: str) -> None:
        now = time.time()
        series = []
        for key in SIGNALS:
            value = snap.get(key)
            if value is None:
                continue
            ts = self.mon.TimeSeries()
            ts.metric.type = f"custom.googleapis.com/tbom/workload/{key}"
            ts.metric.labels["run_tag"] = self.run_tag
            ts.metric.labels["cell"] = cell.lower()
            ts.resource.type = "global"
            ts.resource.labels["project_id"] = self.project
            interval = self.mon.TimeInterval({"end_time": {"seconds": int(now), "nanos": int(now % 1 * 1e9)}})
            ts.points = [self.mon.Point({"interval": interval, "value": {"double_value": float(value)}})]
            series.append(ts)
        try:
            self.client.create_time_series(name=f"projects/{self.project}", time_series=series)
        except Exception as exc:  # noqa: BLE001 - metrics are best-effort; the local ledger is the record
            if not self.warned:
                print(f"  (custom metrics not written: {type(exc).__name__}: {exc})"[:300])
                self.warned = True


def run_grid(args) -> pathlib.Path:
    store, gemini = Store(), Gemini()
    out = HERE / "results" / args.run_tag
    calls = TrackedCalls(Jsonl(out / "calls.jsonl"))
    claims_out, runs_out, samples = Jsonl(out / "claims.jsonl"), Jsonl(out / "runs.jsonl"), Jsonl(out / "samples.jsonl")
    emitter = MetricEmitter(os.environ["GOOGLE_CLOUD_PROJECT"], args.run_tag) if args.emit_metrics else None
    spent, spent_lock = 0.0, threading.Lock()
    base = RUNS[args.config]
    cells = [(rate, frac) for frac in args.fault_rates for rate in args.rates]
    print(f"run_tag={args.run_tag}  design={args.config}  cells={len(cells)}  -> {out}")

    for rate, frac in cells:
        if spent >= args.max_usd:
            print("stopping: --max-usd reached")
            break
        cell = f"G-R{rate}-F{round(frac * 100):02d}"
        claims = store.claims[args.claim_offset : args.claim_offset + rate * args.minutes]
        faulty = pick_faulty(claims, frac)
        cfg = dataclasses.replace(
            base, run_id=cell, title=f"{rate}/min arrivals, {frac:.0%} faulty tool", faults=True, fault_refs=faulty,
        )
        tracker = Tracker()
        calls.tracker = tracker
        agent = Agent(cfg, store, gemini, args.run_tag, calls, claims_out)
        agent.create_caches()
        stop = threading.Event()

        def sample_loop(cell=cell, rate=rate, frac=frac, tracker=tracker, stop=stop):
            while not stop.wait(args.sample_seconds):
                snap = tracker.snapshot()
                samples.write({"run_tag": args.run_tag, "cell": cell, "rate_per_min": rate,
                               "fault_fraction": frac, "t": utcnow().isoformat(), **snap})
                if emitter:
                    emitter.emit(snap, cell)

        def run_one(claim, tracker=tracker, agent=agent):
            nonlocal spent
            try:
                rows = agent.process([claim])
            except Exception as exc:  # noqa: BLE001
                print(f"  {claim['claim_ref']}: {type(exc).__name__}: {exc}"[:200])
                rows = []
            finally:
                tracker.complete(claim["claim_ref"])
            with spent_lock:
                spent += sum(r["cost_usd"] for r in rows)
            return rows

        sampler = threading.Thread(target=sample_loop, daemon=True)
        sampler.start()
        started = utcnow()
        futures = []
        with cf.ThreadPoolExecutor(max_workers=args.max_inflight) as pool:
            for k, claim in enumerate(claims):
                delay = tracker.t0 + k * 60.0 / rate - time.monotonic()
                if delay > 0:
                    time.sleep(delay)
                if spent >= args.max_usd:
                    break
                tracker.admit(claim["claim_ref"])
                futures.append(pool.submit(run_one, claim))
            tracker.phase = "drain"
        rows = [r for f in futures for r in f.result()]
        storage, creation = agent.delete_caches()
        spent += storage + creation
        tracker.phase = "gap"
        time.sleep(args.gap_seconds)
        stop.set()
        sampler.join()

        runs_out.write({
            "run_tag": args.run_tag, "run_id": cell, "title": cfg.title, "n_claims": len(rows),
            "started_at": started.isoformat(), "finished_at": utcnow().isoformat(),
            "cache_storage_usd": round(storage, 6), "cache_creation_usd": round(creation, 6),
            "simulated": gemini.simulated, "rate_per_min": rate, "fault_fraction": frac,
            "faulty_claims": sorted(faulty),
        })
        n = len(rows) or 1
        tokens = sum(r["prompt_tokens"] + r["output_tokens"] + r["thoughts_tokens"] for r in rows)
        print(
            f"{cell:12s} claims={len(rows):3d} faulty={len(faulty):2d} accuracy={sum(r['correct'] for r in rows) / n:6.1%} "
            f"tokens/claim={tokens / n:9,.0f} $/claim={sum(r['cost_usd'] for r in rows) / n:.4f} "
            f"errors={sum(1 for r in rows if r['error'])}"
        )
    print(f"List-price estimate: ${spent:,.2f}.  Next: python workload_grid.py --analyze {out}")
    return out


# ----------------------------------------------------------------------------------------------
# Analysis
# ----------------------------------------------------------------------------------------------


def read_jsonl(path: pathlib.Path) -> list[dict]:
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()] if path.exists() else []


def sustained(points: list[tuple[float, float | None]], threshold: float, seconds: float) -> bool:
    """True if the signal stays above the threshold for at least `seconds` (0 = any single sample)."""
    run_start = None
    for t, v in points:
        if v is not None and v > threshold:
            run_start = t if run_start is None else run_start
            if t - run_start >= seconds:
                return True
        else:
            run_start = None
    return False


def cm_token_rate(project: str, start: dt.datetime, end: dt.datetime) -> list[dict]:
    """Project-wide tokens/min from Cloud Monitoring, the metric the R4 alert policy watches."""
    import google.auth
    from google.cloud import monitoring_v3

    creds, _ = google.auth.default(quota_project_id=project)
    client = monitoring_v3.MetricServiceClient(credentials=creds)
    results = client.list_time_series(
        request={
            "name": f"projects/{project}",
            "filter": 'metric.type="aiplatform.googleapis.com/publisher/online_serving/token_count"',
            "interval": monitoring_v3.TimeInterval(
                {"start_time": {"seconds": int(start.timestamp())}, "end_time": {"seconds": int(end.timestamp())}}
            ),
            "aggregation": monitoring_v3.Aggregation({
                "alignment_period": {"seconds": 60},
                "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_SUM,
                "cross_series_reducer": monitoring_v3.Aggregation.Reducer.REDUCE_SUM,
            }),
            "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
        }
    )
    points = []
    for series in results:
        for p in series.points:
            v = p.value.int64_value or p.value.double_value
            points.append({"t": p.interval.end_time.isoformat(), "tokens_per_min": int(v)})
    return sorted(points, key=lambda p: p["t"])


def backfill_max_calls(samples: list[dict], claims: list[dict], calls: list[dict]) -> None:
    """Rebuilds max_calls_per_claim_1m from the ledgers for grids recorded before that signal existed."""
    ts = dt.datetime.fromisoformat
    done = {(c["run_id"], c["claim_ref"]): ts(c["finished_at"]) for c in claims if c.get("finished_at")}
    begun = {(c["run_id"], c["claim_ref"]): ts(c["started_at"]) for c in claims if c.get("started_at")}
    call_end: dict[tuple, list] = {}
    for c in calls:
        end = ts(c["started_at"]) + dt.timedelta(milliseconds=int(c["latency_ms"]))
        call_end.setdefault((c["run_id"], c["claim_ref"]), []).append(end)
    for s in samples:
        if s.get("max_calls_per_claim_1m") is not None:
            continue
        t = ts(s["t"])
        live = [k for k, b in begun.items() if k[0] == s["cell"] and b <= t and done[k] > t - dt.timedelta(seconds=60)]
        s["max_calls_per_claim_1m"] = max((sum(1 for e in call_end.get(k, []) if e <= t) for k in live), default=0)
        s["backfilled"] = True


def load_grid(out: pathlib.Path, warmup_s: float):
    runs, claims, samples = read_jsonl(out / "runs.jsonl"), read_jsonl(out / "claims.jsonl"), read_jsonl(out / "samples.jsonl")
    cells = [r for r in runs if r.get("rate_per_min")]
    if not cells:
        sys.exit(f"no grid cells in {out}/runs.jsonl")
    backfill_max_calls(samples, claims, read_jsonl(out / "calls.jsonl"))
    by_cell = {r["run_id"]: [s for s in samples if s["cell"] == r["run_id"]] for r in cells}
    evaluated = {c: [s for s in ss if s["phase"] == "arrivals" and s["elapsed_s"] >= warmup_s] for c, ss in by_cell.items()}
    return cells, claims, by_cell, evaluated


def peak_of(evaluated: dict, cell: str, key: str) -> float:
    vals = [s[key] for s in evaluated[cell] if s.get(key) is not None]
    return max(vals) if vals else 0


def calibrate(cells: list[dict], evaluated: dict) -> dict:
    """Every threshold comes from ONE healthy run (the quietest fault-free cell), as the R4 alert did."""
    healthy = [r for r in cells if r["fault_fraction"] == 0] or cells
    calib = min(healthy, key=lambda r: (r["fault_fraction"], r["rate_per_min"]))["run_id"]
    # Fixed alert B: the same alert re-calibrated on the BUSIEST healthy cell ("raise it until busy days stop paging").
    busy = max(healthy, key=lambda r: (r["rate_per_min"], -r["fault_fraction"]))["run_id"]
    return {
        "calib": calib,
        "busy_calib": busy,
        "tokens": 1.2 * peak_of(evaluated, calib, "tokens_per_min"),
        "tokens_busy": 1.2 * peak_of(evaluated, busy, "tokens_per_min"),
        "ratio": 1.2 * peak_of(evaluated, calib, "tokens_per_admitted_claim_3m"),
        "age": max(60.0, 1.5 * peak_of(evaluated, calib, "oldest_inflight_age_s")),
        "calls": 2.0 * peak_of(evaluated, calib, "max_calls_per_claim_1m"),
    }


def analyze(out: pathlib.Path, warmup_s: float, sustain_s: float, cm_check: bool,
            calibrate_on: pathlib.Path | None = None) -> None:
    cells, claims, by_cell, evaluated = load_grid(out, warmup_s)
    source = calibrate_on or out
    if calibrate_on:  # out-of-sample: thresholds come from an earlier grid, not from this one
        ref_cells, _, _, ref_evaluated = load_grid(calibrate_on, warmup_s)
        th = calibrate(ref_cells, ref_evaluated)
    else:
        th = calibrate(cells, evaluated)
    calib, busy_calib = th["calib"], th["busy_calib"]
    t_tokens, t_tokens_busy, t_ratio, t_age, t_calls = th["tokens"], th["tokens_busy"], th["ratio"], th["age"], th["calls"]

    def peak(cell, key):
        return peak_of(evaluated, cell, key)

    cm = []
    if cm_check:
        start = min(dt.datetime.fromisoformat(r["started_at"]) for r in cells) - dt.timedelta(minutes=2)
        end = max(dt.datetime.fromisoformat(r["finished_at"]) for r in cells) + dt.timedelta(minutes=2)
        try:
            cm = cm_token_rate(os.environ["GOOGLE_CLOUD_PROJECT"], start, end)
            Jsonl(out / "cm_token_rate.jsonl").path.write_text("".join(json.dumps(p) + "\n" for p in cm))
        except Exception as exc:  # noqa: BLE001
            print(f"(Cloud Monitoring check skipped: {type(exc).__name__}: {exc})"[:300])

    lines = [
        f"# Workload grid `{out.name}`",
        "",
        f"Thresholds calibrated on the healthy cell `{calib}` of `{source.name}` (arrival window after {warmup_s:.0f} s warm-up):",
        f"- Fixed token-rate alert A: > {t_tokens:,.0f} tokens/min for {sustain_s:.0f} s (1.2x peak of `{calib}`, the R4 method)",
        f"- Fixed token-rate alert B: > {t_tokens_busy:,.0f} tokens/min for {sustain_s:.0f} s (1.2x peak of `{busy_calib}`)",
        f"- Tokens per admitted claim (rolling 3 min): > {t_ratio:,.0f} for {sustain_s:.0f} s (1.2x healthy peak)",
        f"- Oldest unfinished claim: > {t_age:.0f} s (1.5x healthy peak, 60 s floor; age is already a duration)",
        f"- Max model calls by any one claim (last 60 s): > {t_calls:.0f} (2x healthy peak)",
        "",
        "| Cell | Arrivals/min | Faulty claims | Claims | Accuracy | $/claim | Peak tokens/min | Peak tokens/admitted claim | "
        "Peak oldest age (s) | Peak calls by one claim | Fixed alert A | Fixed alert B | Ratio rule | Age rule | "
        "Calls-per-claim rule | Should page? |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in cells:
        c = r["run_id"]
        rows = [x for x in claims if x["run_id"] == c and x["run_tag"] == r["run_tag"]]
        n = len(rows) or 1
        pts = lambda key: [(s["elapsed_s"], s.get(key)) for s in evaluated[c]]  # noqa: E731
        fixed = sustained(pts("tokens_per_min"), t_tokens, sustain_s)
        fixed_b = sustained(pts("tokens_per_min"), t_tokens_busy, sustain_s)
        ratio = sustained(pts("tokens_per_admitted_claim_3m"), t_ratio, sustain_s)
        age = sustained(pts("oldest_inflight_age_s"), t_age, 0)
        per_claim = sustained(pts("max_calls_per_claim_1m"), t_calls, 0)
        should = bool(r["faulty_claims"])

        def mark(fired):
            return ("fires" if fired else "quiet") + (" ✅" if fired == should else " ❌")

        lines.append(
            f"| `{c}` | {r['rate_per_min']} | {len(r['faulty_claims'])} | {len(rows)} | "
            f"{sum(x['correct'] for x in rows) / n:.0%} | {sum(x['cost_usd'] for x in rows) / n:.4f} | "
            f"{peak(c, 'tokens_per_min'):,.0f} | {peak(c, 'tokens_per_admitted_claim_3m'):,.0f} | "
            f"{peak(c, 'oldest_inflight_age_s'):.0f} | {peak(c, 'max_calls_per_claim_1m'):.0f} | {mark(fixed)} | "
            f"{mark(fixed_b)} | {mark(ratio)} | {mark(age)} | {mark(per_claim)} | "
            f"{'yes' if should else 'no'} |"
        )
    if cm:
        lines += ["", "Cloud Monitoring `publisher/online_serving/token_count`, project-wide, 1-minute sums:", ""]
        for r in cells:
            s, e = dt.datetime.fromisoformat(r["started_at"]), dt.datetime.fromisoformat(r["finished_at"])
            vals = [p["tokens_per_min"] for p in cm if s <= dt.datetime.fromisoformat(p["t"]) <= e]
            lines.append(f"- `{r['run_id']}`: peak {max(vals, default=0):,} tokens/min")
    text = "\n".join(lines) + "\n"
    (out / "grid_summary.md").write_text(text, encoding="utf-8")
    print(text)
    plot(out, cells, by_cell, (t_tokens, t_tokens_busy), t_ratio, t_age, t_calls)


def plot(out, cells, by_cell, t_tokens, t_ratio, t_age, t_calls) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(pip install matplotlib for grid_signals.png)")
        return
    panels = [
        ("tokens_per_min", "Tokens per minute", t_tokens, ("fixed alert A", "fixed alert B")),
        ("tokens_per_admitted_claim_3m", "Tokens per admitted claim (3 min)", t_ratio, "ratio rule"),
        ("oldest_inflight_age_s", "Oldest unfinished claim (s)", t_age, "age rule"),
        ("max_calls_per_claim_1m", "Max model calls by one claim (last 60 s)", t_calls, "calls-per-claim rule"),
        ("admitted_per_min", "Admitted claims per minute", None, None),
    ]
    colors = {0.0: "#1a73e8", 0.05: "#f9ab00", 0.2: "#d93025"}
    fig, axes = plt.subplots(len(panels), 1, figsize=(10, 14), sharex=True)
    for ax, (key, title, threshold, label) in zip(axes, panels):
        for r in cells:
            ss = [s for s in by_cell[r["run_id"]] if s["phase"] != "gap" and s.get(key) is not None]
            ax.plot(
                [s["elapsed_s"] / 60 for s in ss], [s[key] for s in ss],
                color=colors.get(r["fault_fraction"], "#5f6368"),
                linestyle="-" if r["rate_per_min"] == max(c["rate_per_min"] for c in cells) else "--",
                label=f"{r['rate_per_min']}/min, {r['fault_fraction']:.0%} faulty",
            )
        for th, lb, ls in zip(threshold if isinstance(threshold, tuple) else (threshold,),
                              label if isinstance(label, tuple) else (label,), (":", "-.")):
            if th:
                ax.axhline(th, color="black", linewidth=1, linestyle=ls, label=lb)
        ax.set_title(title, loc="left", fontsize=11)
        ax.grid(alpha=0.3)
    axes[0].legend(fontsize=8, ncol=2)
    axes[-1].set_xlabel("Minutes since the cell started (solid = busy, dashed = quiet)")
    fig.tight_layout()
    fig.savefig(out / "grid_signals.png", dpi=150)
    print(f"chart: {out / 'grid_signals.png'}")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rates", type=int, nargs="+", default=[4, 8], help="arrivals per minute (quiet, busy)")
    ap.add_argument("--fault-rates", type=float, nargs="+", default=[0.0, 0.05, 0.2], help="faulty-tool fractions")
    ap.add_argument("--minutes", type=int, default=6, help="arrival window per cell")
    ap.add_argument("--config", default="R4U", choices=list(RUNS), help="agent design (R4U = no loop guards)")
    ap.add_argument("--sample-seconds", type=float, default=15.0)
    ap.add_argument("--gap-seconds", type=float, default=60.0, help="idle time between cells")
    ap.add_argument("--max-inflight", type=int, default=64, help="thread cap; set high so arrivals stay open loop")
    ap.add_argument("--max-usd", type=float, default=25.0)
    ap.add_argument("--claim-offset", type=int, default=0, help="start at this claim (fresh claims for a re-test)")
    ap.add_argument("--calibrate-on", type=pathlib.Path, help="with --analyze: take thresholds from another grid")
    ap.add_argument("--run-tag", default=f"grid-{dt.date.today():%m%d}")
    ap.add_argument("--emit-metrics", action="store_true", help="also write the signals to Cloud Monitoring")
    ap.add_argument("--analyze", type=pathlib.Path, help="analyse an existing results directory and exit")
    ap.add_argument("--warmup-seconds", type=float, default=60.0)
    ap.add_argument("--sustain-seconds", type=float, default=60.0)
    ap.add_argument("--cm-check", action="store_true", help="with --analyze: pull token_count from Cloud Monitoring")
    args = ap.parse_args(argv)
    if args.analyze:
        analyze(args.analyze, args.warmup_seconds, args.sustain_seconds, args.cm_check, args.calibrate_on)
        return
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,62}", args.run_tag):
        sys.exit("--run-tag: lowercase letters, digits, '-' or '_' only (it becomes a billing label)")
    out = run_grid(args)
    analyze(out, args.warmup_seconds, args.sustain_seconds, cm_check=False)


if __name__ == "__main__":
    main()
