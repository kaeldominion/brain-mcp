#!/usr/bin/env bash
# Rotate one client's token. Dynamic (clients.yaml) agents rotate instantly —
# no restart; env-managed (static) clients rotate hash + restart brain-mcp.
# Other agents are unaffected. usage: rotate-token.sh <name> [--deploy <prefix>]
set -euo pipefail
cd "$(dirname "$0")/.."
PY=".venv/bin/python"; [[ -x "$PY" ]] || PY="python3"
source scripts/lib/compose.sh

NAME="${1:?usage: rotate-token.sh <name>}"
shift
DEPLOY="$(grep -s '^DEPLOY_PREFIX=' .env | cut -d= -f2)"
DEPLOY="${DEPLOY:-brain}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --deploy) DEPLOY="$2"; shift 2 ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done

set -a; source .env 2>/dev/null; set +a
CLIENTS_FILE="${CLIENTS_DIR:-${VAULT_DIR:?}-clients}/clients.yaml"

if "$PY" scripts/lib/config_edit.py --clients-file "$CLIENTS_FILE" is-dynamic "$NAME" 2>/dev/null; then
  TOKEN=$("$PY" scripts/lib/config_edit.py --clients-file "$CLIENTS_FILE" --deploy "$DEPLOY" rotate-dynamic "$NAME")
  chown 10001:10001 "$CLIENTS_FILE" 2>/dev/null || sudo chown 10001:10001 "$CLIENTS_FILE" 2>/dev/null || true
  echo "rotated token for '$NAME' (dynamic — live immediately)."
elif "$PY" scripts/lib/config_edit.py has-client "$NAME"; then
  TOKEN=$(scripts/generate-secrets.sh "$NAME" --deploy "$DEPLOY" --quiet-token-only)
  compose up -d brain-mcp
  echo "rotated token for '$NAME' (env-managed — brain-mcp restarted)."
else
  echo "error: client '$NAME' not found" >&2
  exit 1
fi

echo ""
echo "  new token: $TOKEN"
echo "  Update the agent's config now — it will NOT be shown again."
