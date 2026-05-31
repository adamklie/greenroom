#!/usr/bin/env bash
# One-command dev start for greenroom.
# - Kills stale backend/vite
# - Clears Vite's optimized-deps cache (stops 504 Outdated Request blanks)
# - Starts backend on :8000 (no --reload; iCloud FS makes reload too flaky)
# - Starts Vite on :5175
# - Waits for each port to be listening and reports health
# Logs: /tmp/greenroom-backend.log, /tmp/greenroom-frontend.log

set -u
ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

echo "→ killing stale processes"
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite.*5175"          2>/dev/null || true
sleep 1

echo "→ clearing Vite optimized-deps cache"
rm -rf "$FRONTEND/node_modules/.vite" 2>/dev/null || true

# Pick a Python that actually has uvicorn. On this machine `python3` resolves
# to Homebrew (no uvicorn) while pyenv's `python` has it — using the wrong one
# silently fails the backend, which surfaces in the UI as the login screen
# (the frontend can't reach /api/auth/me).
PY=""
for cand in python python3; do
  if command -v "$cand" >/dev/null 2>&1 && "$cand" -c "import uvicorn" >/dev/null 2>&1; then
    PY="$cand"; break
  fi
done
if [ -z "$PY" ]; then
  echo "   ✗ no python with uvicorn found (tried: python, python3). Run 'pip install uvicorn' in the right env." >&2
  PY="python3"
fi
echo "→ starting backend with '$PY' (logs: /tmp/greenroom-backend.log)"
( cd "$BACKEND" && nohup "$PY" -m uvicorn app.main:app --port 8000 \
    > /tmp/greenroom-backend.log 2>&1 & ) >/dev/null

echo "→ starting frontend (logs: /tmp/greenroom-frontend.log)"
( cd "$FRONTEND" && nohup npx vite --port 5175 \
    > /tmp/greenroom-frontend.log 2>&1 & ) >/dev/null

wait_for_port() {
  local port="$1"; local name="$2"; local deadline=$(( SECONDS + 60 ))
  while (( SECONDS < deadline )); do
    if curl -s -m 2 -o /dev/null "http://localhost:${port}/"; then
      echo "   ✓ ${name} listening on :${port}"; return 0
    fi
    sleep 1
  done
  echo "   ✗ ${name} did not bind :${port} within 60s — see /tmp/greenroom-${name}.log"
  return 1
}

wait_for_port 8000 backend
wait_for_port 5175 frontend

code=$(curl -s -o /dev/null -m 3 -w "%{http_code}" http://localhost:8000/api/dashboard)
echo "→ backend /api/dashboard returned ${code}"
code=$(curl -s -o /dev/null -m 3 -w "%{http_code}" http://localhost:5175/api/dashboard)
echo "→ vite proxy   /api/dashboard returned ${code}"

echo
echo "Open: http://localhost:5175"
