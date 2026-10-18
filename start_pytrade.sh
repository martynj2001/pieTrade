#!/usr/bin/env bash
# Starts the pyTrade app, the API server and the Angular web app, then opens Firefox.
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
cd "$ROOT" || exit 1

# Use the conda python/uvicorn if they are not already on PATH
export PATH="$HOME/anaconda3/bin:$PATH"

# Hide the harmless Qt "Could not register app ID" portal warning
export QT_LOGGING_RULES="qt.qpa.services=false"

# Check the app's Python libraries before starting anything.
# --dry-run makes pip work out what it WOULD install without changing anything,
# so it fails if a library is missing or at the wrong version.
REQ_FILE="$ROOT/requirements-app.txt"
if [ -f "$REQ_FILE" ]; then
  if ! PIP_OUT=$(python -m pip install --dry-run -q -r "$REQ_FILE" 2>&1); then
    echo "ERROR: Python libraries are missing or out of date."
    echo "$PIP_OUT" | tail -n 5
    echo
    echo "Fix with: python -m pip install -r requirements-app.txt"
    echo "(If you are offline, pip may fail to look up packages. Check your connection.)"
    exit 1
  fi
else
  echo "WARNING: requirements-app.txt not found - skipping library check."
fi

LOG_DIR="$ROOT/log_txt_services"
mkdir -p "$LOG_DIR"
PIDS=()

cleanup() {
  echo "Stopping pyTrade services..."
  for pid in "${PIDS[@]}"; do
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null
  done
  free_port 4200
  free_port 8000
}

free_port() {
  local pids
  pids=$(lsof -ti tcp:"$1" 2>/dev/null || fuser -n tcp "$1" 2>/dev/null)
  if [ -n "$pids" ]; then
    echo "Freeing port $1 (pids: $pids)"
    kill $pids 2>/dev/null; sleep 1
    kill -9 $pids 2>/dev/null
  fi
}

trap cleanup EXIT INT TERM

free_port 4200
free_port 8000

echo "Starting pyTrade app..."
setsid python pyTrade_main.py >"$LOG_DIR/app.log" 2>&1 &
APP_PID=$!; PIDS+=("$APP_PID")

echo "Starting API server..."
setsid uvicorn api.main:app --port 8000 >"$LOG_DIR/api.log" 2>&1 &
PIDS+=("$!")

echo "Starting Angular web app..."
(cd "$ROOT/web" && exec setsid npx ng serve >"$LOG_DIR/web.log" 2>&1) &
PIDS+=("$!")

echo "Waiting for http://localhost:4200 ..."
READY=0
for _ in $(seq 1 120); do
  # Stop waiting early if the app has already died
  if ! kill -0 "$APP_PID" 2>/dev/null; then
    echo "ERROR: pyTrade app exited early. Last lines of app.log:"
    tail -n 20 "$LOG_DIR/app.log"
    exit 1
  fi
  if curl -fs -o /dev/null http://localhost:4200; then READY=1; break; fi
  sleep 1
done

if [ "$READY" -ne 1 ]; then
  echo "ERROR: web app did not start within 120s. Last lines of web.log:"
  tail -n 20 "$LOG_DIR/web.log"
  exit 1
fi

nohup firefox --new-tab http://localhost:4200 >/dev/null 2>&1 &

echo "pyTrade running. Close the pyTrade app window or press Ctrl+C to stop everything."
wait "$APP_PID"