#!/usr/bin/env bash
# Starts the pyTrade app, the API server and the Angular web app, then opens Firefox.
ROOT="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
cd "$ROOT" || exit 1

# Use the conda python/uvicorn if they are not already on PATH
export PATH="$HOME/anaconda3/bin:$PATH"

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
for _ in $(seq 1 120); do
  curl -fs -o /dev/null http://localhost:4200 && break
  sleep 1
done

true

echo "pyTrade running. Close the pyTrade app window or press Ctrl+C to stop everything."
sleep 5
