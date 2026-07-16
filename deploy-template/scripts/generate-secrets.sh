#!/usr/bin/env bash
# Generate a bearer token for one client; store ONLY its sha256 hash in .env.
# The plaintext token is printed once — paste it into the agent's config.
#
# usage: generate-secrets.sh <client-name> [--deploy nnova] [--env-file .env] [--quiet-token-only]
set -euo pipefail
cd "$(dirname "$0")/.."
PY=".venv/bin/python"; [[ -x "$PY" ]] || PY="python3"

CLIENT="${1:?usage: generate-secrets.sh <client-name> [--deploy <prefix>]}"
shift
DEPLOY="$(grep -s '^DEPLOY_PREFIX=' .env | cut -d= -f2)"
DEPLOY="${DEPLOY:-brain}"
ENV_FILE=".env"
QUIET=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --deploy) DEPLOY="$2"; shift 2 ;;
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --quiet-token-only) QUIET=1; shift ;;
    *) echo "unknown option: $1" >&2; exit 1 ;;
  esac
done

SLUG=$(echo "$CLIENT" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '-' | sed 's/-*$//')
TOKEN="${DEPLOY}_${SLUG}_$(openssl rand -hex 16)"
HASH=$(printf %s "$TOKEN" | { shasum -a 256 2>/dev/null || sha256sum; } | cut -d' ' -f1)
ENV_VAR=$("$PY" scripts/lib/config_edit.py env-var "$CLIENT")

touch "$ENV_FILE"
chmod 600 "$ENV_FILE"
if grep -q "^${ENV_VAR}=" "$ENV_FILE"; then
  # portable in-place edit (BSD/GNU sed differ); rewrite via temp file
  awk -v var="$ENV_VAR" -v val="$HASH" -F= 'BEGIN{OFS="="} $1==var{$0=var"="val} {print}' \
    "$ENV_FILE" > "$ENV_FILE.tmp" && mv "$ENV_FILE.tmp" "$ENV_FILE" && chmod 600 "$ENV_FILE"
else
  echo "${ENV_VAR}=${HASH}" >> "$ENV_FILE"
fi

if [[ $QUIET -eq 1 ]]; then
  echo "$TOKEN"
else
  echo ""
  echo "  client : $CLIENT"
  echo "  env var: $ENV_VAR (hash written to $ENV_FILE)"
  echo "  token  : $TOKEN"
  echo ""
  echo "  Paste the token into the agent's config now — it will NOT be shown again."
  echo "  Restart brain-mcp to apply: docker compose up -d brain-mcp"
fi
