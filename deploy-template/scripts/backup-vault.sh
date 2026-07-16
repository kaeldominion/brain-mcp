#!/bin/sh
# Vault backup: git commit + push. One-shot by default; --loop for the sidecar.
# Runs in the alpine/git backup container (vault mounted at /vault) or on the
# host with VAULT_DIR set. Never touches the MCP server; reads are unaffected.
set -eu

VAULT="${VAULT_DIR:-/vault}"
INTERVAL="${BACKUP_INTERVAL_SECONDS:-900}"

backup_once() {
  cd "$VAULT"
  git config --global --add safe.directory "$VAULT" 2>/dev/null || true
  [ -d .git ] || { echo "vault is not a git repo — run bootstrap.sh first" >&2; return 1; }
  if [ -n "${BACKUP_REMOTE:-}" ] && ! git remote get-url origin >/dev/null 2>&1; then
    git remote add origin "$BACKUP_REMOTE"
  fi
  git add -A
  if ! git diff --cached --quiet; then
    git -c user.name=brain-backup -c user.email=backup@localhost \
        commit -qm "vault backup $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  fi
  if git remote get-url origin >/dev/null 2>&1; then
    GIT_SSH_COMMAND="ssh -o StrictHostKeyChecking=accept-new" git push -q origin main || \
      echo "push failed (will retry next cycle)" >&2
  fi
}

if [ "${1:-}" = "--loop" ]; then
  echo "backup loop: every ${INTERVAL}s"
  while true; do
    backup_once || true
    sleep "$INTERVAL"
  done
else
  backup_once
fi
