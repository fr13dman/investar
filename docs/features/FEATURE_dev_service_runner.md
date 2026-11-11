# Feature: One-command service runner (`dev.sh`)

`./dev.sh restart` stops and starts both services, the FastAPI API (port 8010) and the Next.js UI (port 3010), and
waits until each responds before returning.

```bash
./dev.sh start      # start both; refuses if a port is already taken
./dev.sh stop       # stop both
./dev.sh restart    # stop then start
./dev.sh status     # which ports are listening, with PIDs
./dev.sh logs       # follow .run/api.log and .run/web.log
API_PORT=9000 WEB_PORT=4000 ./dev.sh start
```

## How it works

| Concern | Approach |
| --- | --- |
| Starting | Each service runs detached with `nohup` from its own folder: `uv run uvicorn app.main:app` in `backend/`, `pnpm exec next dev --port $WEB_PORT` in `frontend/`. The UI gets `INVESTAR_API_ORIGIN` so its `/api` rewrite targets the chosen API port. |
| Readiness | Polls `GET /api/health` (API) and `/` (UI) for up to 60 s; on timeout it prints the last log lines. |
| PIDs and logs | `.run/api.pid`, `.run/web.pid`, `.run/api.log`, `.run/web.log` (gitignored). |
| Stopping | Kills the recorded PID and its whole child tree (`uv` -> `python`, `pnpm` -> `node`), then any **listener on the port whose working directory is inside this repo**. |
| Safety | A process on the same port from another project is never killed; it is reported instead. This matters here because other local projects use 8000 and 3000. |
| Compatibility | Works with macOS's default bash 3.2 (no `${var^^}`, no `setsid`). |

```bash
# dev.sh: only touch processes that belong to this repo
owned() {
  local cwd
  cwd="$(lsof -a -p "$1" -d cwd -Fn 2>/dev/null | sed -n 's/^n//p' | head -1)"
  [[ "$cwd" == "$ROOT"* ]]
}
```

## Technologies considered

| Option | Why not chosen |
| --- | --- |
| `docker compose` | Adds container builds and volume mounts for a single-user local app; slows the Python and Node dev loops |
| `honcho` / `foreman` (Procfile) | Foreground only (one terminal per session); no restart or status of detached processes |
| `concurrently` npm script | Also foreground; ties the backend lifecycle to a Node process |
| `make` targets | Fine as a wrapper, but process management would still need this shell logic |

## Tests

`scripts/test_dev.sh` runs on spare ports (18010/13010) and checks:

- `start` brings up the API and the UI, and the UI proxies `/api` to the API;
- `status` reports running;
- `restart` replaces the API process and comes back healthy;
- a second `start` refuses busy ports with a clear message;
- `stop` frees both ports;
- a foreign process (a `python -m http.server` started from `/tmp`) on the API port is reported and **not** killed.
