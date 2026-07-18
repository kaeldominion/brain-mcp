#!/usr/bin/env bash
# Fresh-install bootstrap: preflight → seed vault (full template incl. _System/)
# → init backup repo → tooling venv → secrets → start stack → verify.
# Traefik-aware: TRAEFIK_MODE=bundled deploys our Traefik; TRAEFIK_MODE=external
# attaches brain-mcp to an existing Traefik's network (Hostinger default).
# Idempotent: safe to re-run; existing vault content is never overwritten.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=".venv/bin/python"; [[ -x "$PY" ]] || PY="python3"
source scripts/lib/compose.sh

say() { printf '\n==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

say "Preflight"
command -v docker >/dev/null || die "docker is not installed"
docker compose version >/dev/null 2>&1 || die "docker compose v2 is required"
command -v python3 >/dev/null || die "python3 is required"
command -v openssl >/dev/null || die "openssl is required"
[[ -f .env ]] || die "no .env — copy .env.example to .env and fill it in (or run ./brain setup)"
set -a; source .env; set +a
[[ "${VAULT_DIR:-}" && "${AUDIT_DIR:-}" ]] || die "VAULT_DIR and AUDIT_DIR must be set in .env"
CLIENTS_DIR="${CLIENTS_DIR:-${VAULT_DIR}-clients}"
chmod 600 .env

TRAEFIK_MODE="${TRAEFIK_MODE:-bundled}"
if [[ "$TRAEFIK_MODE" == "local" ]]; then
  say "Local mode: personal brain on this machine — MCP on 127.0.0.1:${BRAIN_LOCAL_PORT:-8000}, no reverse proxy"
elif [[ "$TRAEFIK_MODE" == "external" ]]; then
  say "Traefik mode: external (attaching to network '${TRAEFIK_NETWORK:?TRAEFIK_NETWORK required for external mode}')"
  docker network inspect "$TRAEFIK_NETWORK" >/dev/null 2>&1 \
    || die "Docker network '$TRAEFIK_NETWORK' not found — is the existing Traefik running?"
else
  say "Traefik mode: bundled (deploying our Traefik on 80/443)"
  for port in 80 443; do
    if docker ps --format '{{.Ports}}' | grep -q ":${port}->"; then
      docker ps --format '{{.Names}} {{.Ports}}' | grep ":${port}->" | grep -q "^${COMPOSE_PROJECT_NAME:-$(basename "$PWD")}" \
        || die "port $port is already bound by another container — an existing reverse proxy? Set TRAEFIK_MODE=external (./brain setup detects this)"
    fi
  done
fi

BRAIN_IMAGE=$(grep -Eo 'ghcr.io/kaeldominion/brain-mcp:[0-9a-zA-Z.-]+' docker-compose.yml | head -1)
[[ -n "$BRAIN_IMAGE" ]] || die "could not find pinned brain-mcp image in docker-compose.yml"

say "Seeding vault at $VAULT_DIR from $BRAIN_IMAGE"
# plain mkdir first (personal installs under \$HOME need no root); sudo fallback for /srv-style paths
mkdir -p "$VAULT_DIR" "$AUDIT_DIR" "$CLIENTS_DIR" 2>/dev/null || sudo mkdir -p "$VAULT_DIR" "$AUDIT_DIR" "$CLIENTS_DIR"
chmod 700 "$CLIENTS_DIR" 2>/dev/null || sudo chmod 700 "$CLIENTS_DIR"
[[ -w "$VAULT_DIR" ]] || sudo chown "$(id -u)":"$(id -g)" "$VAULT_DIR" "$AUDIT_DIR"   # writable for seeding; handed to the server user below
docker pull -q "$BRAIN_IMAGE" >/dev/null
cid=$(docker create "$BRAIN_IMAGE")
tmpdir=$(mktemp -d)
docker cp "$cid":/opt/vault-template "$tmpdir/vault-template"
docker rm "$cid" >/dev/null
# copy without clobbering anything that already exists (incl. _System/)
(cd "$tmpdir/vault-template" && find . -type d -exec mkdir -p "$VAULT_DIR/{}" \; \
  && find . -type f | while read -r f; do
       [[ -e "$VAULT_DIR/$f" ]] || cp "$f" "$VAULT_DIR/$f"
     done)
rm -rf "$tmpdir"

say "Backup repo"
if [[ ! -d "$VAULT_DIR/.git" ]]; then
  git -C "$VAULT_DIR" init -q -b main
  cat > "$VAULT_DIR/.gitignore" <<'EOF'
.obsidian/workspace*
.trash/
.tmp-*
EOF
  git -C "$VAULT_DIR" add -A
  git -C "$VAULT_DIR" -c user.name=brain-backup -c user.email=backup@localhost commit -qm "initial vault"
  [[ -n "${BACKUP_REMOTE:-}" && "$BACKUP_REMOTE" != *YOUR_ORG* ]] \
    && git -C "$VAULT_DIR" remote add origin "$BACKUP_REMOTE" || true
fi

if [[ "$(uname)" == "Linux" ]]; then
  say "Handing vault + audit + clients ownership to the server user"
  # the server container runs as non-root UID 10001 (baked into the image);
  # without this, reads work but every write fails with 'Permission denied'
  sudo chown -R 10001:10001 "$VAULT_DIR" "$AUDIT_DIR" "$CLIENTS_DIR"
else
  say "macOS/Windows: Docker Desktop maps file ownership automatically — no chown needed"
fi

say "Tooling venv (.venv: pyyaml, rich, questionary)"
[[ -d .venv ]] || python3 -m venv .venv
./.venv/bin/pip install -q --upgrade pip pyyaml rich questionary
PY=".venv/bin/python"

say "Token hashes"
for client in $("$PY" scripts/lib/config_edit.py list-clients | cut -f1); do
  var=$("$PY" scripts/lib/config_edit.py env-var "$client")
  val=$(grep -s "^${var}=" .env | cut -d= -f2 || true)
  if [[ -z "$val" || "$val" == "CHANGE_ME" ]]; then
    say "Generating token for '$client' (hash → .env)"
    scripts/generate-secrets.sh "$client"
  fi
done

say "Compose validation ($TRAEFIK_MODE traefik)"
compose config -q

say "Starting stack"
compose up -d
say "Waiting for brain-mcp health"
state=starting
for i in $(seq 1 30); do
  state=$(compose ps --format '{{.Health}}' brain-mcp 2>/dev/null || echo starting)
  [[ "$state" == "healthy" ]] && break
  sleep 2
done
[[ "$state" == "healthy" ]] || die "brain-mcp did not become healthy; check: docker compose logs brain-mcp"

say "Verification"
scripts/verify.sh || die "verification failed"

say "Bootstrap complete. Onboard each agent with ./brain add-agent (or scripts/add-agent.sh) —"
say "each prints one copyable block (URL + token + skill) to paste into that agent's config."
