#!/usr/bin/env bash
# Acceptance verification against the LIVE stack (brief §17), Traefik-mode aware.
# Host-level checks here; protocol/auth/authz checks run via a scripted
# external MCP test client (lib/verify_inner.py — valid token per role,
# invalid token, no token). Pass agent tokens for the full authed suite:
#   VERIFY_TOKEN_ADMIN=... VERIFY_TOKEN_EDITOR=... VERIFY_TOKEN_CONTRIBUTOR=... scripts/verify.sh
set -uo pipefail
cd "$(dirname "$0")/.."
source scripts/lib/compose.sh

MODE="$(grep -s '^TRAEFIK_MODE=' .env | cut -d= -f2)"
MODE="${MODE:-bundled}"

FAILS=0
check() {  # check <name> <command...>
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "ok $name"; else echo "FAIL $name"; FAILS=$((FAILS+1)); fi
}

echo "— host checks (traefik mode: $MODE) —"
check "compose config valid" compose config -q
check "brain-mcp running" sh -c "$(declare -f compose); compose ps brain-mcp --format '{{.State}}' | grep -q running"
check "brain-mcp healthy" sh -c "$(declare -f compose); compose ps brain-mcp --format '{{.Health}}' | grep -q healthy"
check "mcp port NOT published on host" sh -c "$(declare -f compose); ! compose ps brain-mcp --format '{{.Publishers}}' | grep -Eq '0\.0\.0\.0|\[::\]'"
if [[ "$MODE" == "bundled" ]]; then
  check "bundled traefik publishes 80/443" sh -c "$(declare -f compose); compose ps traefik --format '{{.Publishers}}' | grep -q ':80'"
else
  NET="$(grep -s '^TRAEFIK_NETWORK=' .env | cut -d= -f2)"
  check "external traefik network exists" docker network inspect "$NET"
  check "brain-mcp attached to '$NET'" sh -c "docker network inspect '$NET' -f '{{range .Containers}}{{.Name}} {{end}}' | grep -q brain-mcp"
fi
check "audit dir present" sh -c "set -a; . ./.env; set +a; test -d \"\$AUDIT_DIR\""
if [[ "$(grep -s '^CONSOLE_ENABLED=' .env | cut -d= -f2)" == "true" ]]; then
  check "console running" sh -c "$(declare -f compose); for i in \$(seq 1 15); do compose ps console --format '{{.State}}' | grep -q running && exit 0; sleep 2; done; exit 1"
  check "console healthz" sh -c "$(declare -f compose); compose exec -T console wget -qO- http://127.0.0.1:3000/api/healthz | grep -q true"
fi
check "vault+audit writable by server user" sh -c "$(declare -f compose); compose exec -T brain-mcp python -c \"import tempfile,os; [os.unlink(tempfile.mkstemp(dir=d)[1]) for d in ('/vault','/audit')]\""

echo ""
echo "— token hygiene —"
check "no plaintext tokens in container env" sh -c "$(declare -f compose); ! compose exec -T brain-mcp env | grep -E '^[^=]+=[a-z0-9]+_[a-z0-9-]+_[0-9a-f]{32}$'"
check "no tokens in brain-mcp logs" sh -c "$(declare -f compose); ! compose logs brain-mcp 2>&1 | grep -E '[a-z0-9]+_[a-z0-9-]+_[0-9a-f]{32}'"

echo ""
echo "— protocol / auth / authz (scripted external MCP test client) —"
compose exec -T \
  -e VERIFY_TOKEN_ADMIN="${VERIFY_TOKEN_ADMIN:-}" \
  -e VERIFY_TOKEN_EDITOR="${VERIFY_TOKEN_EDITOR:-}" \
  -e VERIFY_TOKEN_CONTRIBUTOR="${VERIFY_TOKEN_CONTRIBUTOR:-}" \
  brain-mcp python - < scripts/lib/verify_inner.py
INNER=$?

echo ""
if [[ $FAILS -eq 0 && $INNER -eq 0 ]]; then
  echo "VERIFY: all checks passed (traefik mode: $MODE)"
  exit 0
else
  echo "VERIFY: FAILURES detected (host: $FAILS, inner exit: $INNER)"
  exit 1
fi
