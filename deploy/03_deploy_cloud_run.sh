#!/usr/bin/env bash
# =============================================================================
# 03_deploy_cloud_run.sh — Build container via Cloud Build & deploy to Cloud Run
# Usage: bash deploy/03_deploy_cloud_run.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/00_variables.sh"

if ! gcloud artifacts repositories describe "${ARTIFACT_REPO}" \
  --location="${DEPLOY_REGION}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating Artifact Registry repository ${ARTIFACT_REPO} in ${DEPLOY_REGION}..."
  gcloud artifacts repositories create "${ARTIFACT_REPO}" \
    --repository-format=docker \
    --location="${DEPLOY_REGION}" \
    --description="Container images for Cymbal Claims TBOM Agent" \
    --project="${PROJECT_ID}"
fi

IMAGE_TAG="$(date -u +%Y%m%d-%H%M%S)"
IMAGE_URI="${DEPLOY_REGION}-docker.pkg.dev/${PROJECT_ID}/${ARTIFACT_REPO}/${CLOUD_RUN_SERVICE}:${IMAGE_TAG}"

echo "Building container image ${IMAGE_URI} with Cloud Build..."
gcloud builds submit "${REPO_ROOT}" \
  --tag="${IMAGE_URI}" \
  --project="${PROJECT_ID}" \
  --quiet

echo "Deploying ${CLOUD_RUN_SERVICE} to Cloud Run (${DEPLOY_REGION})..."
gcloud run deploy "${CLOUD_RUN_SERVICE}" \
  --image="${IMAGE_URI}" \
  --region="${DEPLOY_REGION}" \
  --project="${PROJECT_ID}" \
  --service-account="${SERVICE_ACCOUNT_EMAIL}" \
  --no-allow-unauthenticated \
  --cpu=1 \
  --memory=2Gi \
  --concurrency=8 \
  --min-instances=0 \
  --max-instances=4 \
  --timeout=300 \
  --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION},GOOGLE_GENAI_USE_VERTEXAI=True,TBOM_RUN_TAG=${TBOM_RUN_TAG},ADK_WEB=true" \
  --quiet

DEPLOYER_ACCOUNT="$(gcloud config get-value account 2>/dev/null || true)"
if [[ -n "${DEPLOYER_ACCOUNT}" ]]; then
  echo "Granting roles/run.invoker to ${DEPLOYER_ACCOUNT} on ${CLOUD_RUN_SERVICE}..."
  gcloud run services add-iam-policy-binding "${CLOUD_RUN_SERVICE}" \
    --region="${DEPLOY_REGION}" \
    --project="${PROJECT_ID}" \
    --member="user:${DEPLOYER_ACCOUNT}" \
    --role="roles/run.invoker" \
    --quiet >/dev/null
fi

SERVICE_URL="$(gcloud run services describe "${CLOUD_RUN_SERVICE}" \
  --region="${DEPLOY_REGION}" --project="${PROJECT_ID}" --format='value(status.url)')"

echo "============================================================================="
echo "Cloud Run deployment complete!"
echo "  Service URL: ${SERVICE_URL}"
echo "  Test with:   python deploy/05_test_deployed_agent.py --cloud-run-url ${SERVICE_URL}"
echo "============================================================================="
