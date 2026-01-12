#!/usr/bin/env bash
set -euo pipefail

if command -v cloudflared >/dev/null 2>&1; then
  echo "Starting cloudflared tunnel for MCP SSE..."
  cloudflared tunnel --url http://127.0.0.1:9000/sse
  exit 0
fi

if command -v ngrok >/dev/null 2>&1; then
  echo "Starting ngrok tunnel for MCP..."
  ngrok http 9000
  echo "\nUse the public URL and append /sse for MCP_SERVER_URL."
  exit 0
fi

echo "No tunnel tool found. Install one of these:" >&2
echo "- cloudflared: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/" >&2
echo "- ngrok: https://ngrok.com/download" >&2
exit 1
