#!/usr/bin/env bash
# Rotate one client's token: new token + hash, restart brain-mcp.
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

"$PY" scripts/lib/config_edit.py has-client "$NAME" \
  || { echo "error: client '$NAME' not found in brain.config.yaml" >&2; exit 1; }

TOKEN=$(scripts/generate-secrets.sh "$NAME" --deploy "$DEPLOY" --quiet-token-only)
compose up -d brain-mcp

echo "rotated token for '$NAME'; the old token is now invalid."
echo ""
echo "  new token: $TOKEN"
echo "  Update the agent's config now — it will NOT be shown again."
