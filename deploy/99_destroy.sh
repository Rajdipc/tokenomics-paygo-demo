#!/usr/bin/env bash
# =============================================================================
# 99_destroy.sh — Complete teardown of all deployed & experiment resources
# Usage: bash deploy/99_destroy.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/00_variables.sh"

echo "Starting teardown in project ${PROJECT_ID}..."

# 1. Delete Cloud Run service if deployed
if gcloud run services describe "${CLOUD_RUN_SERVICE}" \
  --region="${DEPLOY_REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "1. Deleting Cloud Run service ${CLOUD_RUN_SERVICE} (${DEPLOY_REGION})..."
  gcloud run services delete "${CLOUD_RUN_SERVICE}" \
    --region="${DEPLOY_REGION}" --project="${PROJECT_ID}" --quiet
else
  echo "1. Cloud Run service ${CLOUD_RUN_SERVICE} not found (skipping)."
fi

# 2. Delete Gemini Platform Agent Runtime (Agent Engine) instance if deployment_metadata.json exists
if [[ -f "${REPO_ROOT}/deployment_metadata.json" ]]; then
  echo "2. Deleting Gemini Platform Agent Runtime instance from deployment_metadata.json..."
  python3 - <<'PY' || true
import json, pathlib, vertexai
from vertexai import agent_engines

meta_path = pathlib.Path("deployment_metadata.json")
meta = json.loads(meta_path.read_text(encoding="utf-8"))
rid = meta.get("remote_agent_runtime_id")
if rid:
    vertexai.init(project=meta.get("project"), location=meta.get("region", "us-central1"))
    eng = agent_engines.get(rid)
    eng.delete(force=True)
    print(f"Deleted Agent Runtime: {rid}")
meta_path.unlink(missing_ok=True)
PY
else
  echo "2. No deployment_metadata.json found (skipping Agent Runtime deletion)."
fi

# 3. Delete Artifact Registry repository if created
if gcloud artifacts repositories describe "${ARTIFACT_REPO}" \
  --location="${DEPLOY_REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "3. Deleting Artifact Registry repository ${ARTIFACT_REPO}..."
  gcloud artifacts repositories delete "${ARTIFACT_REPO}" \
    --location="${DEPLOY_REGION}" --project="${PROJECT_ID}" --quiet
else
  echo "3. Artifact Registry repository ${ARTIFACT_REPO} not found (skipping)."
fi

# 4. Delete any leftover explicit Gemini context caches
echo "4. Deleting any leftover tbom-* explicit context caches..."
python3 - <<'PY' || true
import os
from google import genai
from google.genai import types

project = os.environ.get("GOOGLE_CLOUD_PROJECT")
if project:
    client = genai.Client(
        vertexai=True,
        project=project,
        location=os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        http_options=types.HttpOptions(api_version="v1"),
    )
    for c in client.caches.list():
        if (c.display_name or "").startswith("tbom-"):
            print("Deleting cache:", c.name, c.display_name)
            client.caches.delete(name=c.name)
PY

# 5. Delete Cloud Monitoring token-burn alert policy if created
echo "5. Checking for 'TBOM demo - Gemini token burn rate' Cloud Monitoring alert policy..."
POLICY_IDS="$(gcloud alpha monitoring policies list --project="${PROJECT_ID}" \
  --filter='displayName="TBOM demo - Gemini token burn rate"' --format='value(name)' 2>/dev/null || true)"
for PID in ${POLICY_IDS}; do
  echo "   Deleting alert policy ${PID}..."
  gcloud alpha monitoring policies delete "${PID}" --project="${PROJECT_ID}" --quiet || true
done

# 6. Delete BigQuery dataset tokenomics_demo if created
echo "6. Dropping BigQuery dataset ${PROJECT_ID}:tokenomics_demo (if present)..."
bq rm -r -f -d "${PROJECT_ID}:tokenomics_demo" 2>/dev/null || true

# 7. Delete runtime service account if created
if gcloud iam service-accounts describe "${SERVICE_ACCOUNT_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "7. Deleting runtime service account ${SERVICE_ACCOUNT_EMAIL}..."
  gcloud iam service-accounts delete "${SERVICE_ACCOUNT_EMAIL}" --project="${PROJECT_ID}" --quiet
else
  echo "7. Service account ${SERVICE_ACCOUNT_EMAIL} not found (skipping)."
fi

echo "Teardown complete for ${PROJECT_ID}."
