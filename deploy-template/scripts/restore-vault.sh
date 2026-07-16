#!/usr/bin/env bash
# Restore the vault from the backup Git repo.
#   restore-vault.sh <path-in-vault> [<commit>]   restore one note (default: last commit that touched it)
#   restore-vault.sh --full <target-dir>          clone the entire backup into an empty directory
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; source .env; set +a

if [[ "${1:-}" == "--full" ]]; then
  TARGET="${2:?usage: restore-vault.sh --full <target-dir>}"
  [[ -e "$TARGET" && -n "$(ls -A "$TARGET" 2>/dev/null)" ]] && { echo "error: $TARGET is not empty" >&2; exit 1; }
  git clone "$BACKUP_REMOTE" "$TARGET"
  echo "Full vault restored to $TARGET. Point VAULT_DIR there (or rsync into place), then: docker compose up -d"
  exit 0
fi

NOTE="${1:?usage: restore-vault.sh <path-in-vault> [<commit>]}"
COMMIT="${2:-}"
cd "$VAULT_DIR"
if [[ -z "$COMMIT" ]]; then
  COMMIT=$(git rev-list -1 HEAD -- "$NOTE")
  [[ -n "$COMMIT" ]] || { echo "error: no history for '$NOTE'" >&2; exit 1; }
fi
git checkout "$COMMIT" -- "$NOTE"
echo "restored '$NOTE' from $COMMIT (working tree only; next backup cycle commits it)"
