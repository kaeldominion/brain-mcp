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

if "$PY" scripts/lib/config_edit.py has-client "$NAME"; then
  echo "error: client '$NAME' already exists in brain.config.yaml" >&2
  exit 1
fi

# 1. config first (validates role exists + single-admin rule), then secrets
"$PY" scripts/lib/config_edit.py add-client "$NAME" --role "$ROLE"
TOKEN=$(scripts/generate-secrets.sh "$NAME" --deploy "$DEPLOY" --quiet-token-only)

# 2. validate the final config with the real server code (same image as prod)
compose run --rm --no-deps --entrypoint python brain-mcp -c \
  "from brain_mcp.config import load_config; load_config('/config/brain.config.yaml'); print('config OK')"

# 3. apply
if [[ $RESTART -eq 1 ]]; then
  compose up -d brain-mcp
  echo "brain-mcp restarted with client '$NAME' (role: $ROLE)" >&2
fi

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
