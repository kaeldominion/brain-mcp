# Shared compose invocation — sourced by every script. One code path for
# both Traefik modes: TRAEFIK_MODE=bundled|external (from .env, default bundled).
# POSIX sh compatible — verify.sh re-executes this function under `sh -c`,
# which is dash on Ubuntu; no bashisms allowed here.
compose() {
  mode="$(grep -s '^TRAEFIK_MODE=' .env | cut -d= -f2)"
  mode="${mode:-bundled}"
  extra=""
  if [ "$(grep -s '^CONSOLE_ENABLED=' .env | cut -d= -f2)" = "true" ]; then
    extra="-f compose.console.yml"
  fi
  case "$mode" in
    bundled)  docker compose -f docker-compose.yml -f compose.bundled-traefik.yml $extra "$@" ;;
    external) docker compose -f docker-compose.yml -f compose.external-traefik.yml $extra "$@" ;;
    local)
      if [ -n "$extra" ]; then
        extra="$extra -f compose.local-console.yml"
      fi
      docker compose -f docker-compose.yml -f compose.local.yml $extra "$@" ;;
    *) echo "error: TRAEFIK_MODE must be 'bundled', 'external' or 'local' (got '$mode')" >&2; return 1 ;;
  esac
}
