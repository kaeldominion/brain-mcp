#!/usr/bin/env bash
# Quick stack health snapshot (used by ./brain status and cron alerting).
set -euo pipefail
cd "$(dirname "$0")/.."
source scripts/lib/compose.sh

echo "— containers —"
compose ps --format 'table {{.Service}}\t{{.State}}\t{{.Health}}'

echo ""
echo "— brain-mcp /health —"
compose exec -T brain-mcp python -c \
  "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=5).read().decode())"

echo ""
echo "— last backup commit —"
set -a; source .env 2>/dev/null; set +a
git -C "${VAULT_DIR:-/vault}" log -1 --format='%h %ad %s' --date=iso 2>/dev/null || echo "(no backup repo)"
