#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID=${PROJECT_ID:?set PROJECT_ID}
REGION=${REGION:-asia-northeast3}
SERVICE=${SERVICE:-stock-ai-mcp}
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE}"

gcloud builds submit --tag "${IMAGE}" mcp

gcloud run deploy "${SERVICE}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --allow-unauthenticated
