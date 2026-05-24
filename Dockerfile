# Greenroom — single-container image.
#
# Stage 1 builds the React frontend with Node. Stage 2 is the runtime:
# python:3.11-slim with FastAPI + ffmpeg + Litestream, serving both the
# /api/* JSON routes and the built SPA out of the same uvicorn process.
#
# At tens-of-viewers scale a backend restart blipping the SPA is fine;
# in exchange we get one Dockerfile, one Fly machine, one set of logs.

# ---- Stage 1: frontend build ----
FROM node:20-alpine AS web
WORKDIR /web

# Copy lockfile + manifest first so `npm ci` is cacheable across source changes.
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Then bring in the rest of the frontend and build.
COPY frontend/ ./
RUN npm run build
# Vite emits to /web/dist (see frontend/vite.config.ts default).


# ---- Stage 2: runtime ----
FROM python:3.11-slim

# ffmpeg for audio extraction (used by /api/upload + trim).
# curl/wget for healthcheck and Litestream tarball; ca-certificates so
# HTTPS replication to R2 works.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ffmpeg ca-certificates curl wget \
    && rm -rf /var/lib/apt/lists/*

# Litestream — continuous SQLite → S3-compatible replication. Phase 3d
# will point it at R2 via env vars; the entrypoint skips it cleanly when
# no R2 creds are present (e.g. local docker compose).
ARG LITESTREAM_VERSION=0.3.13
ADD https://github.com/benbjohnson/litestream/releases/download/v${LITESTREAM_VERSION}/litestream-v${LITESTREAM_VERSION}-linux-amd64.tar.gz /tmp/litestream.tar.gz
RUN tar -C /usr/local/bin -xzf /tmp/litestream.tar.gz && rm /tmp/litestream.tar.gz

WORKDIR /app

# Copy backend source then install. The earlier split (pyproject-only
# install for layer caching, source second) silently broke the package:
# setuptools' packages.find ran before app/ existed, so top_level.txt
# was empty and `python scripts/x.py` couldn't `import app.*`. The app
# still booted because uvicorn runs from /app/backend (cwd on sys.path),
# but anything invoked from a subdir broke. Caching the deps layer
# isn't worth this footgun for a backend that rebuilds on every deploy.
COPY backend/ ./backend/
RUN pip install --no-cache-dir -e ./backend

# Bring the built SPA across from the web stage and tell FastAPI where it lives.
COPY --from=web /web/dist /app/static

# Persistent state lives at /data (a Fly volume in prod, a bind mount in
# docker-compose). PORT mirrors Fly's expected http_service.internal_port.
ENV GREENROOM_DB_PATH=/data/greenroom.db \
    GREENROOM_VAULT_DIR=/data/vault \
    GREENROOM_STATIC_DIR=/app/static \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# Alembic + uvicorn need to be invoked from the backend dir (matches the
# entry script under WORKDIR=/app).
WORKDIR /app/backend

EXPOSE 8080

COPY infra/entrypoint.sh /entrypoint.sh
COPY infra/litestream.yml /etc/litestream.yml
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
