#!/usr/bin/env bash
# Restarts the FastAPI backend in the background and tails its log.
#
# Usage (from the backend/ directory):
#   ./restart_backend.sh
#
# Ctrl+C only stops the log tail — the server keeps running detached.
# Edit VENV_PYTHON below if your virtualenv lives somewhere else.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PYTHON="${VENV_PYTHON:-$SCRIPT_DIR/../.venv/bin/python}"
LOG_FILE="$SCRIPT_DIR/backend.log"
PID_FILE="$SCRIPT_DIR/backend.pid"
HOST="0.0.0.0"
PORT="8000"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Python interpreter not found at: $VENV_PYTHON" >&2
  echo "Set VENV_PYTHON=/path/to/.venv/bin/python before running this script." >&2
  exit 1
fi

echo "Stopping any existing backend process..."
if [[ -f "$PID_FILE" ]]; then
  kill "$(cat "$PID_FILE")" 2>/dev/null
fi
pkill -f "uvicorn app.main:app" 2>/dev/null
sleep 1

echo "Starting backend (host=$HOST port=$PORT)..."
nohup "$VENV_PYTHON" -m uvicorn app.main:app --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
disown
echo $! > "$PID_FILE"

echo "Backend started, pid=$(cat "$PID_FILE"). Log: $LOG_FILE"
echo "Tailing log (Ctrl+C stops tailing only, backend keeps running)..."
tail -f "$LOG_FILE"
