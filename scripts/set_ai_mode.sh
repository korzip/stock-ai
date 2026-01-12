#!/usr/bin/env bash
set -euo pipefail

MODE=${1:-}
if [[ "$MODE" != "rule" && "$MODE" != "llm" ]]; then
  echo "Usage: $0 rule|llm" >&2
  exit 1
fi

ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/backend/.env"
if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE. Copy from backend/.env.example first." >&2
  exit 1
fi

python3 - <<'PY'
import os
from pathlib import Path
mode = os.environ.get("MODE")
path = Path(os.environ.get("ENV_FILE"))
lines = path.read_text().splitlines()
kv = {}
for line in lines:
    if '=' in line and not line.strip().startswith('#'):
        k, v = line.split('=', 1)
        kv[k] = v

if mode == 'rule':
    kv['AI_MODE'] = 'rule'
    kv['FORCE_MCP'] = '1'
else:
    kv['AI_MODE'] = ''
    kv['FORCE_MCP'] = '1'

order = [
    'DATABASE_URL',
    'MCP_URL',
    'MCP_TRANSPORT',
    'MCP_SERVER_URL',
    'OPENAI_API_KEY',
    'OPENAI_MODEL',
    'AI_MODE',
    'FORCE_MCP',
]
seen = set()
out = []
for k in order:
    if k in kv:
        out.append(f"{k}={kv[k]}")
        seen.add(k)
for k, v in kv.items():
    if k not in seen:
        out.append(f"{k}={v}")

path.write_text('\n'.join(out) + "\n")
PY
