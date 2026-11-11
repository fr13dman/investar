#!/usr/bin/env bash
# Smoke test for ./dev.sh on spare ports: start, restart, stop, and the "port owned by another app" guard.
set -euo pipefail
cd "$(dirname "$0")/.."
export API_PORT=18010 WEB_PORT=13010
fail() { echo "FAIL: $*"; ./dev.sh stop >/dev/null 2>&1 || true; exit 1; }
up() { curl -fsS -o /dev/null "$1"; }

./dev.sh start || fail "start"
up "http://127.0.0.1:$API_PORT/api/health" || fail "api not up after start"
up "http://127.0.0.1:$WEB_PORT/api/sectors" || fail "web proxy to api not working"
[[ "$(./dev.sh status)" == *"api: running"* ]] || fail "status"

old_pid=$(cat .run/api.pid)
./dev.sh restart || fail "restart"
[[ "$(cat .run/api.pid)" != "$old_pid" ]] || fail "restart did not replace the api process"
up "http://127.0.0.1:$API_PORT/api/health" || fail "api not up after restart"

./dev.sh start >/tmp/dev_start_twice.log 2>&1 && fail "second start should refuse busy ports"
grep -q "already in use" /tmp/dev_start_twice.log || fail "missing busy-port message"

./dev.sh stop
! up "http://127.0.0.1:$API_PORT/api/health" 2>/dev/null || fail "api still up after stop"
! up "http://127.0.0.1:$WEB_PORT" 2>/dev/null || fail "web still up after stop"

# A process from outside the repo on the port must not be killed.
(cd /tmp && exec python3 -m http.server "$API_PORT" >/dev/null 2>&1) &
foreign=$!
for _ in $(seq 1 40); do lsof -nP -t -iTCP:"$API_PORT" -sTCP:LISTEN >/dev/null 2>&1 && break; sleep 0.25; done
[[ "$(./dev.sh stop)" == *"used by another app"* ]] || { kill "$foreign"; fail "foreign process not reported"; }
kill -0 "$foreign" || fail "foreign process was killed"
kill "$foreign"
echo "PASS: dev.sh start/restart/stop/status"
