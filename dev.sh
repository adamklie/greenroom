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

echo "→ starting backend (logs: /tmp/greenroom-backend.log)"
( cd "$BACKEND" && nohup python3 -m uvicorn app.main:app --port 8000 \
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
