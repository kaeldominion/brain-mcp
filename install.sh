#!/usr/bin/env bash
# 2nd Brain one-command installer — by Sentient Labs
#
#   curl -fsSL https://raw.githubusercontent.com/kaeldominion/brain-mcp/main/install.sh | bash
#
# Optional folder name (default 2nd-brain — one folder per brain):
#   curl -fsSL .../install.sh | bash -s -- my-brain
#
# What it does: fetches the latest deploy kit, stamps it into the folder,
# and launches the guided ./brain setup. Nothing global is installed.
set -euo pipefail

DIR="${1:-2nd-brain}"
REPO="${BRAIN_REPO:-https://github.com/kaeldominion/brain-mcp}"

say() { printf '\n==> %s\n' "$*"; }
die() { printf 'error: %s\n' "$*" >&2; exit 1; }

command -v git >/dev/null || die "git is required"
command -v docker >/dev/null || die "docker is required (install Docker first, then re-run)"
command -v python3 >/dev/null || die "python3 is required"

[[ -e "$DIR" ]] && die "folder '$DIR' already exists — manage that brain with: cd $DIR && ./brain"

say "Fetching the latest 2nd Brain deploy kit"
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
git clone -q --depth 1 "$REPO" "$tmp/repo"
cp -R "$tmp/repo/deploy-template" "$DIR"
chmod +x "$DIR/brain" "$DIR"/scripts/*.sh

say "Installed into ./$DIR"
cd "$DIR"

if [[ "${BRAIN_INSTALL_NO_SETUP:-}" == "1" ]]; then
  say "Skipping setup (BRAIN_INSTALL_NO_SETUP=1). Run: cd $DIR && ./brain setup"
  exit 0
fi

# piped installs (`curl | bash`) leave stdin on the pipe; reattach the
# terminal so the wizard's prompts work
if [[ ! -t 0 && -r /dev/tty ]]; then
  exec ./brain setup < /dev/tty
else
  exec ./brain setup
fi
