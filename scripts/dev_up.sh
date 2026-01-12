#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v docker >/dev/null 2>&1; then
  echo "docker not found. Install Docker Desktop first." >&2
  exit 1
fi

if [ ! -x "$ROOT_DIR/backend/.venv/bin/python" ]; then
  echo "backend venv missing at $ROOT_DIR/backend/.venv" >&2
  echo "Run: (cd backend && python3.12 -m venv .venv && pip install -r requirements.txt)" >&2
  exit 1
fi

if [ ! -x "$ROOT_DIR/mcp/.venv/bin/python" ]; then
  echo "mcp venv missing at $ROOT_DIR/mcp/.venv" >&2
  echo "Run: (cd mcp && python3.12 -m venv .venv && pip install -r requirements.txt)" >&2
  exit 1
fi

trap 'echo "\nShutting down..."; kill "$MCP_PID" "$BACKEND_PID" 2>/dev/null || true' EXIT

echo "Starting infra..."
docker compose -f "$ROOT_DIR/infra/docker-compose.yml" up -d

echo "Starting MCP server..."
cd "$ROOT_DIR/mcp"
"$ROOT_DIR/mcp/.venv/bin/python" -m uvicorn http_app:app --host 0.0.0.0 --port 9000 &
MCP_PID=$!

sleep 0.5

echo "Starting backend server..."
cd "$ROOT_DIR/backend"
"$ROOT_DIR/backend/.venv/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "\nRunning:"
echo "- MCP:     http://127.0.0.1:9000/mcp (streamable HTTP)"
echo "- MCP SSE: http://127.0.0.1:9000/sse"
echo "- Backend: http://127.0.0.1:8000/health"

echo "\nPress Ctrl+C to stop."
wait
