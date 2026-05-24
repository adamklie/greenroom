# Deployment

How Greenroom packages itself into one container, runs locally via
docker-compose, and (in Phase 3d) deploys to Fly.io with Cloudflare R2.

For the higher-level architecture decisions (Fly vs Railway, R2 vs S3,
SQLite + Litestream vs Postgres) see the deployment plan reference;
this doc describes what's actually in the repo today.

---

## Architecture

One image, one container, one process tree. FastAPI serves both
`/api/*` and the built React SPA from a single uvicorn instance. At
tens-of-viewers scale a backend restart blipping the SPA is fine, and
the operational simplicity (one log stream, one healthcheck, one
machine) is worth a lot.

```
container
  /entrypoint.sh
    ├─ if R2 creds present: litestream restore + replicate -exec uvicorn
    └─ otherwise:           uvicorn directly
  uvicorn → FastAPI
                ├─ /api/auth/*    (magic-link, role gates)
                ├─ /api/*         (every other router)
                ├─ /api/health    (Fly healthcheck target)
                └─ /             (StaticFiles → /app/static, SPA)
```

Persistent state lives under `/data`:
- `/data/greenroom.db` — SQLite DB (`GREENROOM_DB_PATH`)
- `/data/vault/` — local vault when `MEDIA_BACKEND=local`
- `/data/music_cache/` — legacy music dir mount (local parity only)

In production these all sit on a Fly volume. Locally they live on a
bind mount at `./local-data` (gitignored).

---

## Image: multi-stage build

`Dockerfile` has two stages:

1. **Stage 1 (`node:20-alpine`)** — `npm ci`, `npm run build` → `/web/dist`.
   Lockfile is copied separately so dependency installs cache across
   application-code changes.
2. **Stage 2 (`python:3.11-slim`)** — installs `ffmpeg`,
   `ca-certificates`, Litestream's prebuilt binary, then
   `pip install -e ./backend`. Copies the built SPA from stage 1 into
   `/app/static` and sets `GREENROOM_STATIC_DIR=/app/static` so the
   mount in `main.py` activates.

Build it:

```bash
docker build -t greenroom .
```

The image is ~600 MB (slim Python + ffmpeg dominates).

---

## Local parity: `docker compose up`

```bash
docker compose up --build
# → http://localhost:8080
```

`docker-compose.yml` runs the same image you'd ship to Fly, with two
adjustments for local use:

| Adjustment | Why |
|---|---|
| `./local-data:/data` bind mount | DB + vault survive `docker compose down`; tear it down whenever you want a clean slate. |
| iCloud music dir mounted **read-only** at `/data/music_cache` | The container can resolve legacy paths but can't accidentally clobber real files. |
| `AUTH_REQUIRED=false`, `EMAIL_BACKEND=stub` | Matches `dev.sh` — open the page and you're "logged in" as the synthetic admin. |
| No `R2_*` env vars | `entrypoint.sh` sees no creds and runs uvicorn directly with no Litestream replication. |

To smoke-test:

```bash
curl http://localhost:8080/api/health
curl -I http://localhost:8080/        # → 200, serves index.html
curl http://localhost:8080/api/dashboard
```

Teardown:

```bash
docker compose down            # stops and removes the container
rm -rf local-data              # nukes the DB + vault for a clean restart
```

---

## Env vars: local vs prod

| Var | Local (compose) | Prod (Fly) |
|---|---|---|
| `GREENROOM_DB_PATH` | `/data/greenroom.db` | `/data/greenroom.db` |
| `GREENROOM_VAULT_DIR` | `/data/vault` | `/data/vault` |
| `GREENROOM_MUSIC_DIR` | `/data/music_cache` (ro mount) | unset (legacy not used in prod) |
| `GREENROOM_STATIC_DIR` | `/app/static` | `/app/static` |
| `GREENROOM_MEDIA_BACKEND` | `local` | `r2` |
| `GREENROOM_AUTH_REQUIRED` | `false` | `true` |
| `GREENROOM_AUTH_SECRET` | `dev-secret-change-me` | `fly secrets set …` |
| `GREENROOM_EMAIL_BACKEND` | `stub` | `resend` |
| `GREENROOM_ALLOWED_ORIGINS` | (uses default localhost list) | `fly secrets set https://greenroom.<domain>` |
| `GREENROOM_PUBLIC_URL` | `http://localhost:5175` (default) | `https://greenroom.<domain>` |
| `R2_*` | unset (Litestream skipped) | `fly secrets set …` |
| `RESEND_API_KEY` | unset (stub emailer) | `fly secrets set …` |

The `GREENROOM_ALLOWED_ORIGINS` setting is comma-separated. In prod
it'll be a single hosted origin (CORS doesn't need localhost there);
locally it falls back to the dev defaults so `./dev.sh` keeps working.

---

## Litestream behaviour

`infra/litestream.yml` is a template; every value interpolates from env
vars at container runtime. `infra/entrypoint.sh` checks for
`R2_ACCESS_KEY_ID + R2_SECRET_ACCESS_KEY + R2_BUCKET`:

- **All three present** → `litestream restore -if-replica-exists` (no-op on
  first boot when no replica exists yet), then `litestream replicate
  -exec uvicorn` so every WAL write streams to R2.
- **Any missing** → uvicorn runs directly with no replication. This is
  the local-compose path; the iCloud auto-backup in
  `services/auto_backup.py` still handles backups via the bind mount.

DB backups go to a SEPARATE bucket from media (`R2_DB_BACKUP_BUCKET`,
default `greenroom-db-backups`). Keeping them apart means an `rclone
sync` of the media tree can't accidentally clobber DB snapshots, and a
media-only API token can be issued for bulk-upload scripts.

Retention is 30 days (`720h` in `litestream.yml`).

---

## Phase 3d — Fly.io deploy (DO NOT RUN YET)

After R2 + Resend signups complete, the deploy looks roughly like:

```bash
# One-time
fly apps create greenroom                          # or a unique variant
fly volumes create data --region sea --size 3      # /data mount

# Secrets — replace each <…> with the real value from the provider dashboards
fly secrets set \
    R2_ACCOUNT_ID=<id> \
    R2_ACCESS_KEY_ID=<key> \
    R2_SECRET_ACCESS_KEY=<secret> \
    R2_BUCKET=greenroom-media \
    R2_DB_BACKUP_BUCKET=greenroom-db-backups \
    GREENROOM_AUTH_SECRET=$(openssl rand -hex 32) \
    RESEND_API_KEY=<key> \
    GREENROOM_ALLOWED_ORIGINS=https://greenroom.<domain> \
    GREENROOM_PUBLIC_URL=https://greenroom.<domain>

# Ongoing
fly deploy                                         # builds + deploys
fly logs                                           # tail
fly ssh console                                    # poke around
```

`fly.toml` already declares the volume mount, ports, and non-secret env.
The `app` and `primary_region` keys are placeholders — update them once
`fly apps create` confirms a name.

After the first successful deploy:

```bash
# Bootstrap the first admin user inside the container
fly ssh console -C "cd /app/backend && python scripts/create_admin.py aklie@ucsd.edu"
```

The CORS allow-list in `backend/app/main.py` is now env-driven
(`GREENROOM_ALLOWED_ORIGINS`), so Phase 3d doesn't need a code change to
authorize the hosted domain.

---

## Phase 3e — bulk media upload (DO NOT RUN YET)

Once R2 is live and Phase 3d's `CloudVaultBackend` is wired:

```bash
brew install rclone
rclone config                # add a Cloudflare R2 remote
rclone sync \
    "$HOME/Library/Mobile Documents/com~apple~CloudDocs/music" \
    r2:greenroom-media \
    --exclude "greenroom/**" \
    --exclude "_trash/**" \
    --exclude ".DS_Store" \
    --progress
```

Idempotent (re-runs only upload changed files). Plan for 2-4 hours on
residential upload for the ~33 GB tree.

---

## Troubleshooting

**Image build fails on `apt-get install ffmpeg`** — Docker daemon needs
network access. Check your proxy or try `--network=host` (Linux).

**`docker compose up` exits with "no such file or directory" for the
iCloud mount** — the path in `docker-compose.yml` is hardcoded to
`~/Library/Mobile Documents/com~apple~CloudDocs/music`. Edit it if your
music dir lives elsewhere, or drop the mount entirely if you don't need
legacy path resolution.

**Litestream restore fails on first deploy** — `-if-replica-exists`
should make it a no-op when no replica exists yet, but a malformed env
var or wrong endpoint surfaces as a startup error. Check `fly logs` for
the actual S3 error.

**SPA serves but `/api/*` 404s** — the static mount happens AFTER router
registration in `main.py`. If you see this, you've probably mounted
something at `/` earlier in the chain by accident.

**Hard refresh on `/sessions` returns 404 instead of the SPA** — the
StaticFiles mount needs `html=True`. Verify the line in `main.py`.

---

## Files

| Path | Purpose |
|---|---|
| `Dockerfile` | Multi-stage build (node → python-slim runtime) |
| `.dockerignore` | Keeps build context small; excludes live DB |
| `docker-compose.yml` | Local parity stack |
| `fly.toml` | Fly.io deployment config (Phase 3d) |
| `infra/entrypoint.sh` | Litestream wrapper around uvicorn |
| `infra/litestream.yml` | Replication config template (R2) |
| `backend/app/main.py` | Static mount + env-driven CORS |
| `backend/app/config.py` | `static_dir` + `allowed_origins` settings |
