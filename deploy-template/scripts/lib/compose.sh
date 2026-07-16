# Shared compose invocation — sourced by every script. One code path for
# both Traefik modes: TRAEFIK_MODE=bundled|external (from .env, default bundled).
compose() {
  local mode
  mode="$(grep -s '^TRAEFIK_MODE=' .env | cut -d= -f2)"
  mode="${mode:-bundled}"
  case "$mode" in
    bundled)  docker compose -f docker-compose.yml -f compose.bundled-traefik.yml "$@" ;;
    external) docker compose -f docker-compose.yml -f compose.external-traefik.yml "$@" ;;
    *) echo "error: TRAEFIK_MODE must be 'bundled' or 'external' (got '$mode')" >&2; return 1 ;;
  esac
}
