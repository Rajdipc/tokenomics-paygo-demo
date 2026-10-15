"""05_test_deployed_agent.py — Smoke-test the Cymbal Claims TBOM Agent locally, on Cloud Run, or on Agent Runtime.

Usage:
    # 1. Test local in-process ADK Runner (default if no URL/ID passed):
    python deploy/05_test_deployed_agent.py --claim-ref CLM-000001

    # 2. Test deployed Cloud Run service (authenticates via gcloud identity token):
    python deploy/05_test_deployed_agent.py --cloud-run-url https://cymbal-claims-tbom-agent-...run.app --claim-ref CLM-000001

    # 3. Test deployed Gemini Platform Agent Runtime (reads deployment_metadata.json if --agent-runtime-id='auto'):
    python deploy/05_test_deployed_agent.py --agent-runtime-id auto --claim-ref CLM-000001
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def _gcloud_id_token() -> str:
    res = subprocess.run(
        ["gcloud", "auth", "print-identity-token"],
        capture_output=True,
        text=True,
        check=True,
    )
    return res.stdout.strip()


def test_cloud_run(base_url: str, claim_ref: str, inject_faults: bool = False) -> dict:
    base = base_url.rstrip("/")
    token = _gcloud_id_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # 1. Check /api/health
    req_health = urllib.request.Request(f"{base}/api/health", headers=headers, method="GET")
    with urllib.request.urlopen(req_health, timeout=30) as resp:
        health = json.loads(resp.read().decode("utf-8"))
    print("Cloud Run /api/health:", json.dumps(health, indent=2))

    # 2. Adjudicate claim via /api/adjudicate
    payload = json.dumps({"claim_ref": claim_ref, "inject_faults": inject_faults}).encode("utf-8")
    req_adj = urllib.request.Request(f"{base}/api/adjudicate", data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(req_adj, timeout=180) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    print(f"\nCloud Run /api/adjudicate ({claim_ref}):")
    print(json.dumps(result, indent=2))
    return result


def test_agent_runtime(resource_id: str, claim_ref: str) -> list:
    if resource_id == "auto":
        meta_path = REPO_ROOT / "deployment_metadata.json"
        if not meta_path.exists():
            sys.exit("deployment_metadata.json not found. Run deploy/04_deploy_agent_runtime.py first.")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        resource_id = meta["remote_agent_runtime_id"]

    import google.auth
    import vertexai
    from vertexai import agent_engines
    from cymbal_claims_agent import claim_text, get_default_store

    store = get_default_store()
    claim = store.claims_by_ref.get(claim_ref, store.claims[0])
    prompt = claim_text(claim)

    parts = resource_id.split("/")
    project = parts[1] if len(parts) >= 2 else os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = parts[3] if len(parts) >= 4 else os.environ.get("DEPLOY_REGION", "us-central1")
    os.environ["GOOGLE_CLOUD_QUOTA_PROJECT"] = str(project)
    creds, _ = google.auth.default(quota_project_id=project)
    vertexai.init(project=project, location=location, credentials=creds)

    remote_agent = agent_engines.get(resource_id)
    print(f"Querying Agent Runtime {resource_id} with {claim_ref}...")
    events = list(remote_agent.stream_query(user_id="adjuster", message=prompt))
    print(f"Received {len(events)} stream events from Agent Runtime:")
    print(json.dumps(events[-1] if events else {}, indent=2, default=str))
    return events


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--claim-ref", default="CLM-000001", help="Claim ID from data/incoming_claims.jsonl")
    ap.add_argument("--cloud-run-url", default=None, help="Deployed Cloud Run URL")
    ap.add_argument("--agent-runtime-id", default=None, help="ReasoningEngine resource name or 'auto'")
    ap.add_argument("--inject-faults", action="store_true", help="Simulate upstream fraud timeout")
    args = ap.parse_args()

    if args.cloud_run_url:
        test_cloud_run(args.cloud_run_url, args.claim_ref, args.inject_faults)
    elif args.agent_runtime_id:
        test_agent_runtime(args.agent_runtime_id, args.claim_ref)
    else:
        from cymbal_claims_agent import adjudicate_claim_with_adk

        res = asyncio.run(adjudicate_claim_with_adk(args.claim_ref, inject_faults=args.inject_faults))
        print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
