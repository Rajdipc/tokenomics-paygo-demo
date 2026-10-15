#!/usr/bin/env bash
# =============================================================================
# 02_service_account_iam.sh — Create least-privilege runtime service account
# Usage: bash deploy/02_service_account_iam.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/00_variables.sh"

if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "Creating service account ${SERVICE_ACCOUNT_EMAIL}..."
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --display-name="Cymbal Claims TBOM Agent Runtime SA" \
    --project="${PROJECT_ID}"
  sleep 5
else
  echo "Service account ${SERVICE_ACCOUNT_EMAIL} already exists."
fi

ROLES=(
  "roles/aiplatform.user"
  "roles/cloudtrace.agent"
  "roles/logging.logWriter"
  "roles/monitoring.metricWriter"
)

for ROLE in "${ROLES[@]}"; do
  echo "Granting ${ROLE} to ${SERVICE_ACCOUNT_EMAIL}..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role="${ROLE}" \
    --condition=None \
    --quiet >/dev/null
done

echo "Service account ${SERVICE_ACCOUNT_EMAIL} is ready with least-privilege IAM roles."
