#!/bin/sh
set -u

dsh_pid=""
relay_pid=""

stop_children() {
  trap - INT TERM HUP
  if [ -n "${dsh_pid}" ]; then
    kill -TERM "${dsh_pid}" 2>/dev/null || true
  fi
  if [ -n "${relay_pid}" ]; then
    kill -TERM "${relay_pid}" 2>/dev/null || true
  fi
  if [ -n "${dsh_pid}" ]; then
    wait "${dsh_pid}" 2>/dev/null || true
  fi
  if [ -n "${relay_pid}" ]; then
    wait "${relay_pid}" 2>/dev/null || true
  fi
}

handle_signal() {
  stop_children
  exit 143
}

trap handle_signal INT TERM HUP

mkdir -p "${DSH_HOME:-/home/node/.dsh}" "${HOME:-/workspace}"

if [ "$#" -eq 0 ]; then
  set -- --profile web --no-open --port 3080
fi

is_web=0
if [ "${1:-}" = web ] || { [ "${1:-}" = --profile ] && [ "${2:-}" = web ]; }; then
  is_web=1
fi
for argument in "$@"; do
  case "${argument}" in
    --help|-h|--version|--dump-config|--dump-config-schema) is_web=0 ;;
  esac
done

if [ "${is_web}" = 1 ]; then
  node /opt/dsh-image/dsh-web-relay.cjs "$$" "$@" &
  relay_pid=$!
fi

# Extra trust / public URL for reverse proxies (Tailscale nginx, etc.).
# Example: DSH_WEB_EXTRA_ARGS='--public-url http://100.84.0.2:3080 --trusted-host 100.84.0.2:3080'
# shellcheck disable=SC2086
dsh "$@" ${DSH_WEB_EXTRA_ARGS:-} &
dsh_pid=$!

wait "${dsh_pid}"
status=$?
stop_children
exit "${status}"
