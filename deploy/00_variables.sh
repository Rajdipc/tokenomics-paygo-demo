#!/usr/bin/env bash
# =============================================================================
# 00_variables.sh — Load and validate environment variables (no hardcoded project IDs)
# Usage: source deploy/00_variables.sh
# =============================================================================

if [[ -f ".env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

if [[ -z "${GOOGLE_CLOUD_PROJECT:-}" || "${GOOGLE_CLOUD_PROJECT}" == "your-project-id" ]]; then
  DETECTED_PROJECT="$(gcloud config get-value project 2>/dev/null || true)"
  if [[ -n "${DETECTED_PROJECT}" && "${DETECTED_PROJECT}" != "(unset)" ]]; then
    export GOOGLE_CLOUD_PROJECT="${DETECTED_PROJECT}"
  else
    echo "ERROR: Set GOOGLE_CLOUD_PROJECT in .env or run 'gcloud config set project YOUR_PROJECT_ID'." >&2
    return 1 2>/dev/null || exit 1
  fi
fi

export PROJECT_ID="${GOOGLE_CLOUD_PROJECT}"
export GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-global}"
export GOOGLE_GENAI_USE_VERTEXAI="${GOOGLE_GENAI_USE_VERTEXAI:-True}"
export TBOM_RUN_TAG="${TBOM_RUN_TAG:-exp-tbom}"
export DEPLOY_REGION="${DEPLOY_REGION:-us-central1}"
export CLOUD_RUN_SERVICE="${CLOUD_RUN_SERVICE:-cymbal-claims-tbom-agent}"
export ARTIFACT_REPO="${ARTIFACT_REPO:-cymbal-claims-tbom}"
export SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-cymbal-claims-agent-sa}"
export SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
export AGENT_RUNTIME_DISPLAY_NAME="${AGENT_RUNTIME_DISPLAY_NAME:-cymbal-claims-tbom-agent}"
export STAGING_BUCKET="${STAGING_BUCKET:-gs://${PROJECT_ID}-tbom-agent-staging}"

echo "Loaded configuration:"
echo "  PROJECT_ID                 = ${PROJECT_ID}"
echo "  GOOGLE_CLOUD_LOCATION      = ${GOOGLE_CLOUD_LOCATION}"
echo "  DEPLOY_REGION              = ${DEPLOY_REGION}"
echo "  CLOUD_RUN_SERVICE          = ${CLOUD_RUN_SERVICE}"
echo "  ARTIFACT_REPO              = ${ARTIFACT_REPO}"
echo "  SERVICE_ACCOUNT_EMAIL      = ${SERVICE_ACCOUNT_EMAIL}"
echo "  AGENT_RUNTIME_DISPLAY_NAME = ${AGENT_RUNTIME_DISPLAY_NAME}"
