#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "Starting backend (FastAPI) ..."
(
  cd "$ROOT/backend"
  if [[ -f "venv/bin/python" ]]; then
    exec ./venv/bin/python -m uvicorn src.main:app --reload
  else
    exec python3 -m uvicorn src.main:app --reload
  fi
) &
BACK_PID=$!

echo "Starting frontend (Vite) ..."
(
  cd "$ROOT/frontend"
  exec npm run dev
) &
FRONT_PID=$!

trap 'kill $BACK_PID $FRONT_PID 2>/dev/null; exit' INT TERM

wait
