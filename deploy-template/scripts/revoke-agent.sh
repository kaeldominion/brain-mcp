#!/usr/bin/env bash
# Revoke an agent. Dynamic (clients.yaml) agents die instantly — no restart;
# env-managed (static) clients are removed from config + restart.
# The admin client cannot be revoked. usage: revoke-agent.sh <name>
set -euo pipefail
cd "$(dirname "$0")/.."
PY=".venv/bin/python"; [[ -x "$PY" ]] || PY="python3"
source scripts/lib/compose.sh

NAME="${1:?usage: revoke-agent.sh <name>}"

set -a; source .env 2>/dev/null; set +a
CLIENTS_FILE="${CLIENTS_DIR:-${VAULT_DIR:?}-clients}/clients.yaml"

if "$PY" scripts/lib/config_edit.py --clients-file "$CLIENTS_FILE" is-dynamic "$NAME" 2>/dev/null; then
  "$PY" scripts/lib/config_edit.py --clients-file "$CLIENTS_FILE" remove-dynamic "$NAME"
  chown 10001:10001 "$CLIENTS_FILE" 2>/dev/null || sudo chown 10001:10001 "$CLIENTS_FILE" 2>/dev/null || true
  echo "revoked '$NAME' (dynamic — effective immediately)."
else
  "$PY" scripts/lib/config_edit.py remove-client "$NAME"
  compose run --rm --no-deps --entrypoint python brain-mcp -c \
    "from brain_mcp.config import load_config; load_config('/config/brain.config.yaml'); print('config OK')"
  compose up -d brain-mcp
  echo "revoked '$NAME' (env-managed — brain-mcp restarted)."
fi
echo "Its notes and audit history remain in the vault; only access is gone."
