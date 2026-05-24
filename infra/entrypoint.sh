#!/usr/bin/env bash
# Container entrypoint.
#
# Two modes:
#   1. R2 creds present  → restore DB from the latest replica (no-op if
#      one doesn't exist yet), then run uvicorn under `litestream replicate`
#      so every subsequent commit streams its WAL to R2. This is the
#      production path on Fly.
#   2. No R2 creds       → run uvicorn directly. This is the docker-compose
#      / local-parity path, where the DB lives on a bind mount and backups
#      are handled by the existing iCloud auto-backup mechanism.

set -euo pipefail

: "${PORT:=8080}"
: "${GREENROOM_DB_PATH:=/data/greenroom.db}"

# Make sure the parent dir exists; first boot won't have created it yet
# and Litestream + SQLite both expect to write into a real directory.
mkdir -p "$(dirname "$GREENROOM_DB_PATH")"

UVICORN_CMD=(uvicorn app.main:app --host 0.0.0.0 --port "${PORT}")

if [ -n "${R2_ACCESS_KEY_ID:-}" ] && [ -n "${R2_SECRET_ACCESS_KEY:-}" ] && [ -n "${R2_BUCKET:-}" ]; then
  # Defensively handle stale WAL/SHM and corrupted DBs from a previous
  # crash or DB swap. Three cases:
  #   a) DB exists + integrity_check ok  → just clear any stale wal/shm.
  #      (WAL files from a prior process can confuse SQLite if the .db
  #      was swapped under them — exactly what hit us during the first
  #      Phase 3e cutover attempt.)
  #   b) DB exists + integrity_check fails → preserve as .corrupt-<ts>,
  #      delete wal/shm, and fall through to litestream restore.
  #   c) DB does not exist → fall through to litestream restore.
  if [ -f "${GREENROOM_DB_PATH}" ]; then
    if python3 -c "import sqlite3,sys; db=sqlite3.connect('${GREENROOM_DB_PATH}'); r=db.execute('PRAGMA integrity_check').fetchone(); db.close(); sys.exit(0 if r==('ok',) else 1)" 2>/dev/null; then
      echo "[entrypoint] local DB integrity ok; clearing any stale wal/shm"
      rm -f "${GREENROOM_DB_PATH}-wal" "${GREENROOM_DB_PATH}-shm"
    else
      TS=$(date +%Y%m%d-%H%M%S)
      echo "[entrypoint] WARN local DB FAILED integrity check; preserving as ${GREENROOM_DB_PATH}.corrupt-${TS} and restoring from R2"
      mv "${GREENROOM_DB_PATH}" "${GREENROOM_DB_PATH}.corrupt-${TS}"
      rm -f "${GREENROOM_DB_PATH}-wal" "${GREENROOM_DB_PATH}-shm"
    fi
  fi

  # Restore from replica only when there is no local DB. Either we started
  # fresh, or the integrity check above moved a corrupted file aside.
  if [ ! -f "${GREENROOM_DB_PATH}" ]; then
    echo "[entrypoint] no local DB; restoring from R2 if a replica exists"
    litestream restore -if-replica-exists -config /etc/litestream.yml "${GREENROOM_DB_PATH}"
  else
    echo "[entrypoint] local DB present at ${GREENROOM_DB_PATH}"
  fi
  echo "[entrypoint] starting litestream replicate + uvicorn"
  exec litestream replicate -config /etc/litestream.yml -exec "${UVICORN_CMD[*]}"
else
  echo "[entrypoint] no R2 creds; starting uvicorn without litestream replication"
  exec "${UVICORN_CMD[@]}"
fi
