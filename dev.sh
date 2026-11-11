#!/usr/bin/env bash
# Start / stop / restart the Investar API (FastAPI) and UI (Next.js) together.
#   ./dev.sh start | stop | restart | status | logs
# Ports: API_PORT (default 8010), WEB_PORT (default 3010). Logs and PIDs live in .run/.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN="$ROOT/.run"
API_PORT="${API_PORT:-8010}"
WEB_PORT="${WEB_PORT:-3010}"
mkdir -p "$RUN"

say() { printf '%s\n' "$*"; }

listener_pids() { lsof -nP -t -iTCP:"$1" -sTCP:LISTEN 2>/dev/null; }

# Only touch processes whose working directory is inside this repo (never another project on the same port).
owned() {
  local cwd
  cwd="$(lsof -a -p "$1" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)"
  [[ "$cwd" == "$ROOT"* ]]
}

kill_tree() {
  local pid=$1 child
  for child in $(pgrep -P "$pid" 2>/dev/null); do kill_tree "$child"; done
  kill "$pid" 2>/dev/null
}

stop_service() {
  local name=$1 port=$2 pidfile="$RUN/$1.pid" pid
  if [[ -f "$pidfile" ]]; then
    pid="$(cat "$pidfile")"
    kill -0 "$pid" 2>/dev/null && kill_tree "$pid"
    rm -f "$pidfile"
  fi
  for pid in $(listener_pids "$port"); do
    if owned "$pid"; then kill_tree "$pid"; else say "  port $port is used by another app (pid $pid); leaving it alone"; fi
  done
  for _ in $(seq 1 20); do
    [[ -z "$(listener_pids "$port")" ]] && break
    sleep 0.25
  done
  say "  $name stopped"
}

wait_for() {
  local name=$1 url=$2 log=$3
  for _ in $(seq 1 120); do
    if curl -fsS -o /dev/null "$url" 2>/dev/null; then say "  $name ready: $url"; return 0; fi
    sleep 0.5
  done
  say "  $name did not become ready; last log lines:"; tail -n 15 "$log"; return 1
}

start_service() {
  local name=$1 port=$2 dir=$3 url=$4; shift 4
  if [[ -n "$(listener_pids "$port")" ]]; then
    say "  $name: port $port already in use (run ./dev.sh restart or set $(echo "$name" | tr a-z A-Z)_PORT)"; return 1
  fi
  (cd "$dir" && exec nohup "$@" >"$RUN/$name.log" 2>&1) &
  echo $! >"$RUN/$name.pid"
  wait_for "$name" "$url" "$RUN/$name.log"
}

start() {
  say "Starting Investar"
  start_service api "$API_PORT" "$ROOT/backend" "http://127.0.0.1:$API_PORT/api/health" \
    uv run uvicorn app.main:app --host 127.0.0.1 --port "$API_PORT" || return 1
  INVESTAR_API_ORIGIN="http://127.0.0.1:$API_PORT" \
    start_service web "$WEB_PORT" "$ROOT/frontend" "http://127.0.0.1:$WEB_PORT" \
    env INVESTAR_API_ORIGIN="http://127.0.0.1:$API_PORT" pnpm exec next dev --port "$WEB_PORT" || return 1
  say "Open http://localhost:$WEB_PORT  (logs: ./dev.sh logs)"
}

stop() {
  say "Stopping Investar"
  stop_service web "$WEB_PORT"
  stop_service api "$API_PORT"
}

status() {
  local name port pids
  for pair in "api:$API_PORT" "web:$WEB_PORT"; do
    name="${pair%%:*}"; port="${pair##*:}"; pids="$(listener_pids "$port" | tr '\n' ' ')"
    if [[ -n "$pids" ]]; then say "$name: running on :$port (pid $pids)"; else say "$name: stopped"; fi
  done
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) status ;;
  logs) tail -n 50 -F "$RUN/api.log" "$RUN/web.log" ;;
  *) say "usage: ./dev.sh {start|stop|restart|status|logs}"; exit 2 ;;
esac
