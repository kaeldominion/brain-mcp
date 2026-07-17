#!/usr/bin/env bash
# Add a new agent (an EXTERNAL MCP client — Hermes agents are deployed
# separately and are never part of this stack): generate token, append client
# block to brain.config.yaml, validate config, hot-restart brain-mcp, then
# print ONE copyable block (URL + token + skill) — pasting that into the
# agent's deployment config is the entire integration.
#
# usage: add-agent.sh <name> --role <role> [--deploy <prefix>] [--no-restart]
set -euo pipefail
cd "$(dirname "$0")/.."
PY=".venv/bin/python"; [[ -x "$PY" ]] || PY="python3"
source scripts/lib/compose.sh

NAME="${1:?usage: add-agent.sh <name> --role <role>}"
shift
ROLE=""
DEPLOY="$(grep -s '^DEPLOY_PREFIX=' .env | cut -d= -f2)"
DEPLOY="${DEPLOY:-brain}"
RESTART=1
while [[ $# -gt 0 ]]; do
  case "$1" in
    --role) ROLE="$2"; shift 2 ;;
    --deploy) DEPLOY="$2"; shift 2 ;;
    --no-restart) RESTART=0; shift ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done
[[ -n "$ROLE" ]] || { echo "error: --role is required" >&2; exit 1; }

# agents go into the DYNAMIC registry (clients.yaml): hot-reloaded by the
# server (no restart) and manageable from the web console afterwards
set -a; source .env 2>/dev/null; set +a
CLIENTS_DIR="${CLIENTS_DIR:-${VAULT_DIR:?}-clients}"
CLIENTS_FILE="$CLIENTS_DIR/clients.yaml"

TOKEN=$("$PY" scripts/lib/config_edit.py --clients-file "$CLIENTS_FILE" --deploy "$DEPLOY" \
  add-dynamic "$NAME" --role "$ROLE")

# the server (uid 10001) must be able to read what we just wrote as root
chown 10001:10001 "$CLIENTS_FILE" 2>/dev/null || sudo chown 10001:10001 "$CLIENTS_FILE" 2>/dev/null || true
echo "agent '$NAME' (role: $ROLE) is live — no restart needed" >&2

DOMAIN="$(grep -s '^COMPANY_DOMAIN=' .env | cut -d= -f2)"
cat <<EOF

──── agent onboarding block for '$NAME' — copy everything below ────
# MCP connection (this token is shown ONCE; only its hash is stored)
mcp_servers:
  company_brain:
    url: "https://brain-mcp.${DOMAIN:-<COMPANY_DOMAIN>}/mcp"
    headers:
      Authorization: "Bearer $TOKEN"
    timeout: 120
    connect_timeout: 30

$(cat skills/company-brain.md | sed -n '/^---$/,$p' | tail -n +2)
────────────────────────────────────────────────────────────────────
EOF
