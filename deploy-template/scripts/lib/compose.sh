# Shared compose invocation — sourced by every script. One code path for
# both Traefik modes: TRAEFIK_MODE=bundled|external (from .env, default bundled).
compose() {
  local mode extra=""
  mode="$(grep -s '^TRAEFIK_MODE=' .env | cut -d= -f2)"
  mode="${mode:-bundled}"
  [[ "$(grep -s '^CONSOLE_ENABLED=' .env | cut -d= -f2)" == "true" ]] && extra="-f compose.console.yml"
  case "$mode" in
    bundled)  docker compose -f docker-compose.yml -f compose.bundled-traefik.yml $extra "$@" ;;
    external) docker compose -f docker-compose.yml -f compose.external-traefik.yml $extra "$@" ;;
    *) echo "error: TRAEFIK_MODE must be 'bundled' or 'external' (got '$mode')" >&2; return 1 ;;
  esac
}
