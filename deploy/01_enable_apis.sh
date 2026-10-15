#!/usr/bin/env bash
# =============================================================================
# 01_enable_apis.sh — Enable required Google Cloud APIs for the TBOM Agent
# Usage: bash deploy/01_enable_apis.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/00_variables.sh"

echo "Enabling required Google Cloud APIs in project ${PROJECT_ID}..."
gcloud services enable \
  aiplatform.googleapis.com \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  bigquery.googleapis.com \
  monitoring.googleapis.com \
  cloudtrace.googleapis.com \
  logging.googleapis.com \
  storage.googleapis.com \
  --project="${PROJECT_ID}"

echo "All required APIs are enabled in ${PROJECT_ID}."
