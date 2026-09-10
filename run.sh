#!/usr/bin/env bash
# Starts the API and the frontend together. Ctrl-C stops both.
set -euo pipefail
cd "$(dirname "$0")"

API_PORT="${API_PORT:-8000}"
UI_PORT="${UI_PORT:-5173}"

if [ ! -x .venv/bin/python ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv
    uv pip install -r requirements-dev.txt -e .
  else
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements-dev.txt -e .
  fi
fi

[ -d frontend/node_modules ] || (cd frontend && npm install)

# A stale dev server on either port is the single most confusing failure here:
# Vite quietly starts on the next free port instead, and the app loads but
# cannot reach the API. Say so plainly rather than drifting.
for port in "$API_PORT" "$UI_PORT"; do
  if (command -v lsof >/dev/null && lsof -ti ":$port" >/dev/null 2>&1); then
    echo "Port $port is already in use — stop that process first, or set" >&2
    echo "  API_PORT=... UI_PORT=... ./run.sh" >&2
    exit 1
  fi
done

.venv/bin/uvicorn casting.api:app --port "$API_PORT" --reload &
API=$!
trap 'kill $API 2>/dev/null || true' EXIT

# Wait for the API to answer before starting the UI. Uvicorn's reloader takes a
# couple of seconds, and the frontend fetches its config once on load — racing
# it produces a page that says the backend is unreachable while it is merely
# still booting.
printf 'waiting for the API on :%s' "$API_PORT"
for _ in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:$API_PORT/api/health" >/dev/null 2>&1; then
    echo " — up"
    break
  fi
  if ! kill -0 "$API" 2>/dev/null; then
    echo; echo "The API exited during startup. Its error is above." >&2
    exit 1
  fi
  printf '.'
  sleep 0.5
done

cd frontend && npm run dev -- --port "$UI_PORT" --strictPort
