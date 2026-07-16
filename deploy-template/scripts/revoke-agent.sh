#!/usr/bin/env bash
# Revoke an agent: remove its client block from brain.config.yaml and restart.
# The admin client cannot be revoked. usage: revoke-agent.sh <name>
set -euo pipefail
cd "$(dirname "$0")/.."
PY=".venv/bin/python"; [[ -x "$PY" ]] || PY="python3"
source scripts/lib/compose.sh

NAME="${1:?usage: revoke-agent.sh <name>}"

"$PY" scripts/lib/config_edit.py remove-client "$NAME"
compose run --rm --no-deps --entrypoint python brain-mcp -c \
  "from brain_mcp.config import load_config; load_config('/config/brain.config.yaml'); print('config OK')"
compose up -d brain-mcp
echo "revoked '$NAME'; its token no longer authenticates."
