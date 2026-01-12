#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID=${PROJECT_ID:?set PROJECT_ID}
REGION=${REGION:-asia-northeast3}
SERVICE=${SERVICE:-stock-ai-backend}
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE}"

# Cloud SQL 연결이 필요한 경우에만 설정하세요.
CLOUD_SQL_CONNECTION_NAME=${CLOUD_SQL_CONNECTION_NAME:-}

gcloud builds submit --tag "${IMAGE}" backend

if [[ -n "${CLOUD_SQL_CONNECTION_NAME}" ]]; then
  gcloud run deploy "${SERVICE}" \
    --image "${IMAGE}" \
    --region "${REGION}" \
    --allow-unauthenticated \
    --add-cloudsql-instances "${CLOUD_SQL_CONNECTION_NAME}" \
    --set-env-vars "DATABASE_URL=${DATABASE_URL}" \
    --set-env-vars "OPENAI_API_KEY=${OPENAI_API_KEY}" \
    --set-env-vars "OPENAI_MODEL=${OPENAI_MODEL}" \
    --set-env-vars "MCP_SERVER_URL=${MCP_SERVER_URL}" \
    --set-env-vars "MCP_TRANSPORT=sse" \
    --set-env-vars "FORCE_MCP=1"
else
  gcloud run deploy "${SERVICE}" \
    --image "${IMAGE}" \
    --region "${REGION}" \
    --allow-unauthenticated \
    --set-env-vars "DATABASE_URL=${DATABASE_URL}" \
    --set-env-vars "OPENAI_API_KEY=${OPENAI_API_KEY}" \
    --set-env-vars "OPENAI_MODEL=${OPENAI_MODEL}" \
    --set-env-vars "MCP_SERVER_URL=${MCP_SERVER_URL}" \
    --set-env-vars "MCP_TRANSPORT=sse" \
    --set-env-vars "FORCE_MCP=1"
fi
