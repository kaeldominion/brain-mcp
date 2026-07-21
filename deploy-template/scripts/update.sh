#!/usr/bin/env bash
# One-command update: fetch the latest deploy template from GitHub, refresh
# everything EXCEPT your local state (.env, brain.config.yaml, .venv, vault),
# adopt the template's pinned server image, restart, verify.
#
# usage: update.sh [repo-url]
set -euo pipefail
cd "$(dirname "$0")/.."

REPO_URL="${1:-https://github.com/kaeldominion/brain-mcp}"

echo "==> Fetching latest template from $REPO_URL"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
git clone -q --depth 1 "$REPO_URL" "$tmp/repo"
SRC="$tmp/repo/deploy-template"
[[ -d "$SRC" ]] || { echo "error: deploy-template/ not found in $REPO_URL" >&2; exit 1; }

OLD_PIN=$(grep -Eo 'brain-mcp:[0-9A-Za-z.-]+' docker-compose.yml | head -1 || true)
NEW_PIN=$(grep -Eo 'brain-mcp:[0-9A-Za-z.-]+' "$SRC/docker-compose.yml" | head -1 || true)

echo "==> Refreshing template files (your .env / brain.config.yaml / vault are untouched)"
for item in brain scripts docs skills traefik docker-compose.yml \
            compose.bundled-traefik.yml compose.external-traefik.yml \
            compose.console.yml compose.local.yml compose.local-console.yml \
            .env.example README.md .gitignore; do
  if [[ -e "$SRC/$item" ]]; then
    rm -rf "./${item:?}"
    cp -R "$SRC/$item" "./$item"
  fi
done
chmod +x brain scripts/*.sh 2>/dev/null || true

if [[ -n "$NEW_PIN" && "$NEW_PIN" != "$OLD_PIN" ]]; then
  echo "==> Server version: ${OLD_PIN:-none} -> $NEW_PIN"
else
  echo "==> Server version unchanged (${OLD_PIN:-unknown})"
fi

if [[ -f .env ]]; then
  source scripts/lib/compose.sh
  set -a; . ./.env; set +a

  # config migration: pre-registry installs lack clients_file, so the console /
  # API can't manage agents. Add it (and its host dir) — the only edit update
  # ever makes to brain.config.yaml, and only when the key is absent.
  if [[ -f brain.config.yaml ]] && ! grep -q '^clients_file:' brain.config.yaml; then
    echo "==> Enabling the dynamic client registry (adding clients_file)"
    CLIENTS_DIR="${CLIENTS_DIR:-${VAULT_DIR}-clients}"
    mkdir -p "$CLIENTS_DIR" 2>/dev/null || sudo mkdir -p "$CLIENTS_DIR"
    [[ "$(uname)" == "Linux" ]] && { chown -R 10001:10001 "$CLIENTS_DIR" 2>/dev/null || sudo chown -R 10001:10001 "$CLIENTS_DIR"; }
    if grep -q '^audit_dir:' brain.config.yaml; then
      sed -i.bak '/^audit_dir:/a\
clients_file: /clients/clients.yaml' brain.config.yaml && rm -f brain.config.yaml.bak
    else
      printf '\nclients_file: /clients/clients.yaml\n' >> brain.config.yaml
    fi
  fi

  echo "==> Pulling image + restarting"
  compose pull -q
  compose up -d
  echo "==> Seeding NEW system notes (existing vault files are never touched)"
  set -a; . ./.env; set +a
  NEW_IMAGE=$(grep -Eo 'ghcr.io/kaeldominion/brain-mcp:[0-9A-Za-z.-]+' docker-compose.yml | head -1)
  cid=$(docker create "$NEW_IMAGE")
  seedtmp=$(mktemp -d)
  docker cp "$cid":/opt/vault-template "$seedtmp/vault-template" >/dev/null
  docker rm "$cid" >/dev/null
  added=0
  (cd "$seedtmp/vault-template" && find . -type f | while read -r f; do
     if [ ! -e "$VAULT_DIR/$f" ]; then
       mkdir -p "$VAULT_DIR/$(dirname "$f")"
       cp "$f" "$VAULT_DIR/$f"
       echo "    + ${f#./}"
     fi
   done)
  rm -rf "$seedtmp"
  chown -R 10001:10001 "$VAULT_DIR" 2>/dev/null || sudo chown -R 10001:10001 "$VAULT_DIR" 2>/dev/null || true

  echo "==> Waiting for brain-mcp health"
  state=starting
  for i in $(seq 1 30); do
    state=$(compose ps --format '{{.Health}}' brain-mcp 2>/dev/null || echo starting)
    [[ "$state" == "healthy" ]] && break
    sleep 2
  done
  echo "==> Verifying"
  scripts/verify.sh
else
  echo "==> No .env yet (not installed) — template refreshed only. Run ./brain setup."
fi

echo ""
echo "update complete."
