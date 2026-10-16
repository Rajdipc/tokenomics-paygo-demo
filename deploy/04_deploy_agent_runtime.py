"""04_deploy_agent_runtime.py — Deploy the ADK Cymbal Claims Agent to Gemini Platform Agent Runtime (Agent Engine).

Usage:
    source deploy/00_variables.sh
    python deploy/04_deploy_agent_runtime.py

Writes the deployed ReasoningEngine resource name to ``deployment_metadata.json``
so ``deploy/05_test_deployed_agent.py`` and ``deploy/99_destroy.sh`` can locate it
automatically without hardcoding resource IDs.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))


def ensure_staging_bucket(project: str, region: str, bucket_uri: str) -> None:
    res = subprocess.run(
        ["gcloud", "storage", "buckets", "describe", bucket_uri, f"--project={project}"],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        print(f"Creating staging bucket {bucket_uri} in {region}...")
        subprocess.run(
            [
                "gcloud",
                "storage",
                "buckets",
                "create",
                bucket_uri,
                f"--project={project}",
                f"--location={region}",
                "--uniform-bucket-level-access",
            ],
            check=True,
        )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=os.environ.get("GOOGLE_CLOUD_PROJECT"))
    ap.add_argument("--region", default=os.environ.get("DEPLOY_REGION", "us-central1"))
    ap.add_argument(
        "--display-name",
        default=os.environ.get("AGENT_RUNTIME_DISPLAY_NAME", "cymbal-claims-tbom-agent"),
    )
    args = ap.parse_args()

    if not args.project or args.project == "your-project-id":
        sys.exit("Set GOOGLE_CLOUD_PROJECT in .env or pass --project.")

    bucket_uri = os.environ.get("STAGING_BUCKET") or f"gs://{args.project}-tbom-agent-staging"
    ensure_staging_bucket(args.project, args.region, bucket_uri)

    os.environ["GOOGLE_CLOUD_QUOTA_PROJECT"] = args.project
    import google.auth
    import vertexai
    from vertexai import agent_engines
    from vertexai.agent_engines.templates.adk import AdkApp

    from cymbal_claims_agent.agent import app as adk_app

    creds, _ = google.auth.default(quota_project_id=args.project)
    print(f"Initializing Gemini Platform (Vertex AI) in project={args.project}, location={args.region}...")
    vertexai.init(
        project=args.project,
        location=args.region,
        staging_bucket=bucket_uri,
        credentials=creds,
    )

    deployable_app = AdkApp(app=adk_app)
    requirements = [
        "google-genai>=2.20.0",
        "google-adk>=2.5.0,<3.0.0",
        "google-cloud-aiplatform[agent-engines]>=1.90.0",
        "pydantic>=2.7.0",
    ]
    extra_packages = ["cymbal_claims_agent", "data", "skills"]

    print(f"Deploying {args.display_name!r} to Gemini Platform Agent Runtime (this takes ~3-6 minutes)...")
    remote_agent = agent_engines.create(
        deployable_app,
        requirements=requirements,
        extra_packages=extra_packages,
        display_name=args.display_name,
        description="Cymbal Insurance R5 Claims Agent with Token Bill of Materials (TBOM) telemetry",
        env_vars={
            "GOOGLE_CLOUD_LOCATION": os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
            "GOOGLE_GENAI_USE_VERTEXAI": "True",
            "TBOM_RUN_TAG": os.environ.get("TBOM_RUN_TAG", "agent-runtime"),
        },
    )

    resource_name = remote_agent.resource_name
    meta = {
        "remote_agent_runtime_id": resource_name,
        "deployment_target": "agent_runtime",
        "display_name": args.display_name,
        "project": args.project,
        "region": args.region,
        "staging_bucket": bucket_uri,
        "deployment_timestamp": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    meta_path = REPO_ROOT / "deployment_metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print("=" * 77)
    print("Gemini Platform Agent Runtime deployment complete!")
    print(f"  Resource Name: {resource_name}")
    print(f"  Metadata file: {meta_path}")
    print(f"  Test with:     python deploy/05_test_deployed_agent.py --agent-runtime-id {resource_name}")
    print("=" * 77)


if __name__ == "__main__":
    main()
