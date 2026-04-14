#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# ── Python deps via uv ─────────────────────────────────────────────────────
# uv reads backend/pyproject.toml, creates backend/.venv, and installs
# runtime + optional dev deps.
echo "Installing Python dependencies with uv…"
(cd "$BACKEND_DIR" && uv sync --all-extras)

# ── Data directory ─────────────────────────────────────────────────────────
mkdir -p "$BACKEND_DIR/data"

# ── .env ───────────────────────────────────────────────────────────────────
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  ROOT_ENV="$(dirname "$SCRIPT_DIR")/.env"
  if [ -f "$ROOT_ENV" ]; then
    cp "$ROOT_ENV" "$SCRIPT_DIR/.env"
    echo "Copied .env from $ROOT_ENV"
  fi
fi

# ── Start FastAPI backend (skip if already running) ─────────────────────────
port_in_use() {
  local port=$1
  if command -v lsof >/dev/null 2>&1; then
    lsof -iTCP:"$port" -sTCP:LISTEN -t >/dev/null 2>&1
  elif command -v ss >/dev/null 2>&1; then
    ss -tlnp 2>/dev/null | grep -q ":$port "
  else
    (echo >/dev/tcp/127.0.0.1/"$port") 2>/dev/null
  fi
}

if port_in_use 8000; then
  echo "Port 8000 already in use — assuming FastAPI is already running."
else
  echo "Starting FastAPI on port 8000…"
  cd "$SCRIPT_DIR"
  uv --project "$BACKEND_DIR" run uvicorn backend.main:app --reload --port 8000 &
  BACKEND_PID=$!
  echo "FastAPI started (PID $BACKEND_PID)"
fi

# ── Frontend ───────────────────────────────────────────────────────────────
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "Installing frontend dependencies with bun…"
  cd "$FRONTEND_DIR"
  bun install
fi

if port_in_use 5173; then
  echo "Port 5173 already in use — assuming Vite is already running."
  # Keep script alive
  wait
else
  echo "Starting Vite dev server on port 5173…"
  cd "$FRONTEND_DIR"
  bun run dev
fi

# Cleanup backend on exit
if [ -n "$BACKEND_PID" ]; then
  kill "$BACKEND_PID" 2>/dev/null || true
fi
