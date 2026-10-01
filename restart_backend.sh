#!/usr/bin/env bash
# Pulls latest code, rebuilds the frontend, and restarts the FastAPI backend — run after every push.
#
# Usage (from the repo root):
#   ./restart_backend.sh
#
# Ctrl+C only stops the log tail — the server keeps running detached.
# Edit VENV_PYTHON below if your virtualenv lives somewhere else.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"
FRONTEND_DIR="$REPO_ROOT/frontend/port_optim"
cd "$BACKEND_DIR"

VENV_PYTHON="${VENV_PYTHON:-$HOME/work/.venv/bin/python}"
LOG_FILE="$BACKEND_DIR/backend.log"
PID_FILE="$BACKEND_DIR/backend.pid"
HOST="0.0.0.0"
PORT="8000"

if [[ ! -x "$VENV_PYTHON" ]]; then
  echo "Python interpreter not found at: $VENV_PYTHON" >&2
  echo "Set VENV_PYTHON=/path/to/.venv/bin/python before running this script." >&2
  exit 1
fi

echo "Pulling latest code..."
( cd "$REPO_ROOT" && git stash && git pull )

echo "Stopping any existing backend process..."
if [[ -f "$PID_FILE" ]]; then
  kill "$(cat "$PID_FILE")" 2>/dev/null
fi
pkill -f "uvicorn app.main:app" 2>/dev/null
sleep 1

echo "Starting backend (host=$HOST port=$PORT)..."
setsid nohup "$VENV_PYTHON" -m uvicorn app.main:app --host "$HOST" --port "$PORT" < /dev/null > "$LOG_FILE" 2>&1 &
disown
echo $! > "$PID_FILE"

echo "Backend started, pid=$(cat "$PID_FILE"). Log: $LOG_FILE"

echo "Building frontend ($FRONTEND_DIR)..."
( cd "$FRONTEND_DIR" && npm run build )

echo "Tailing log (Ctrl+C stops tailing only, backend keeps running)..."
tail -f "$LOG_FILE"
