#!/usr/bin/env bash
# MineGuard AI — Phase 1 — startup script (Linux/macOS)
#
# Starts the FastAPI backend and the Vite dev server together.
# Usage:
#   ./start.sh              # start with no camera pre-selected
#   ./start.sh webcam       # start backend with webcam pre-opened

set -e
cd "$(dirname "$0")"

SOURCE_ARG=""
if [ "$1" = "webcam" ]; then
  SOURCE_ARG="--source webcam"
fi

echo "== MineGuard AI: starting backend =="
cd backend
if [ ! -d ".venv" ]; then
  echo "Creating Python virtual environment (.venv)..."
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt
python app.py $SOURCE_ARG &
BACKEND_PID=$!
cd ..

echo "== MineGuard AI: starting frontend =="
cd frontend
if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "Press Ctrl+C to stop both."

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
