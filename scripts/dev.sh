#!/bin/sh
set -eu

P1_5_PYTHON="${P1_5_PYTHON:-python3}"
P1_5_PORT="${PORT:-8000}"

export APP_ENV="${APP_ENV:-development}"
export AI_PROVIDER="${AI_PROVIDER:-mock}"
export AUTH_MODE="${AUTH_MODE:-dev}"
export DATABASE_URL="${DATABASE_URL:-sqlite:///./data/p1_5_capture.sqlite3}"
export ALLOWED_ORIGINS="${ALLOWED_ORIGINS:-http://127.0.0.1:${P1_5_PORT}}"

exec "$P1_5_PYTHON" -m uvicorn backend.app:app \
  --host 127.0.0.1 \
  --port "$P1_5_PORT"
