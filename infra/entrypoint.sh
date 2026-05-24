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
  # Restore from replica only when there is no local DB yet. Litestream's
  # -if-replica-exists flag handles "no backup in bucket" but NOT "local
  # DB already present" — and on every redeploy the Fly volume keeps the
  # existing /data/greenroom.db, so a naked restore crashes the boot loop
  # with "cannot restore, output path already exists".
  if [ ! -f "${GREENROOM_DB_PATH}" ]; then
    echo "[entrypoint] no local DB; restoring from R2 if a replica exists"
    litestream restore -if-replica-exists -config /etc/litestream.yml "${GREENROOM_DB_PATH}"
  else
    echo "[entrypoint] local DB present at ${GREENROOM_DB_PATH}; skipping restore"
  fi
  echo "[entrypoint] starting litestream replicate + uvicorn"
  exec litestream replicate -config /etc/litestream.yml -exec "${UVICORN_CMD[*]}"
else
  echo "[entrypoint] no R2 creds; starting uvicorn without litestream replication"
  exec "${UVICORN_CMD[@]}"
fi
