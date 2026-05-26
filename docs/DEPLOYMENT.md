# Deployment

How Greenroom is packaged into one container, run locally via docker-compose, and deployed to Fly.io with Cloudflare R2 + Resend.

For the higher-level architecture (Fly vs Railway, R2 vs S3, SQLite + Litestream vs Postgres), see [ARCHITECTURE.md](ARCHITECTURE.md). This doc is the runbook.

---

## Architecture

One image, one container, one process tree. FastAPI serves both `/api/*` and the built React SPA from a single uvicorn instance. At tens-of-viewers scale, a backend restart blipping the SPA is fine, and the operational simplicity (one log stream, one healthcheck, one machine) is worth a lot.

```
container
  /entrypoint.sh
    ├─ if local DB exists: integrity-check it
    │     ├─ ok    → clear stale wal/shm
    │     └─ bad   → move aside as .corrupt-<ts>, restore from R2
    ├─ if local DB missing: litestream restore -if-replica-exists
    └─ litestream replicate -exec uvicorn  (prod, R2 creds present)
        OR
        uvicorn directly                   (dev, no R2 creds)
  uvicorn → FastAPI
                ├─ /api/auth/*    magic-link + role gates
                ├─ /api/*         every other router
                ├─ /api/health    Fly healthcheck target
                └─ /              StaticFiles → /app/static, SPA
```

Persistent state lives under `/data`:

| Path | Purpose |
|---|---|
| `/data/greenroom.db` | SQLite DB |
| `/data/vault/backups/` | Startup snapshots (last 10) |
| `/data/greenroom.db.corrupt-<ts>` | Anything moved aside by the boot integrity check |

In production this is a 3 GB encrypted Fly volume. Locally it's a bind mount at `./local-data` (gitignored).

---

## Image

`Dockerfile` is two stages:

1. **`node:20-alpine`** — `npm ci && npm run build` → `/web/dist`.
2. **`python:3.11-slim`** — installs `ffmpeg`, `ca-certificates`, Litestream binary; `pip install -e ./backend` AFTER copying the source (this ordering matters — see Troubleshooting); copies the built SPA from stage 1 to `/app/static`.

Build it:

```bash
docker build -t greenroom .
```

Image size ~259 MB.

---

## Local parity — `docker compose up`

```bash
docker compose up --build
# → http://localhost:8080
```

Local mode runs the same image you'd ship to Fly, with three adjustments:

| Adjustment | Why |
|---|---|
| `./local-data:/data` bind mount | DB + vault survive `docker compose down` |
| iCloud music dir mounted **read-only** at `/data/music_cache` | Container can resolve legacy paths but can't clobber real files |
| No `R2_*` env vars | Entrypoint skips Litestream, runs uvicorn directly |

Smoke-test:

```bash
curl http://localhost:8080/api/health
curl -I http://localhost:8080/                # 200, serves index.html
curl http://localhost:8080/api/dashboard       # 401 (auth required) or 200 (dev mode)
```

Teardown:

```bash
docker compose down
rm -rf local-data         # nukes the DB + vault for a clean restart
```

---

## Production env vars

| Var | Local (compose) | Prod (Fly) |
|---|---|---|
| `GREENROOM_DB_PATH` | `/data/greenroom.db` | `/data/greenroom.db` |
| `GREENROOM_VAULT_DIR` | `/data/vault` | `/data/vault` |
| `GREENROOM_STATIC_DIR` | `/app/static` | `/app/static` |
| `GREENROOM_MEDIA_BACKEND` | `local` | `r2` |
| `GREENROOM_AUTH_REQUIRED` | `false` | `true` |
| `GREENROOM_EMAIL_BACKEND` | `stub` | `resend` |
| `GREENROOM_PUBLIC_URL` | `http://localhost:5175` (default) | `https://greenroom-1.fly.dev` |
| `GREENROOM_ALLOWED_ORIGINS` | (dev defaults) | `https://greenroom-1.fly.dev` |
| `GREENROOM_AUTH_SECRET` | dev-only default | Fly secret (32-byte hex) |
| `GREENROOM_R2_*` | unset | Fly secrets — see below |
| `R2_*` (unprefixed) | unset | Fly secrets — see below |
| `GREENROOM_RESEND_API_KEY` | unset (stub emailer) | Fly secret |
| `GREENROOM_RESEND_FROM_EMAIL` | unset | `Greenroom <onboarding@resend.dev>` or your verified-domain sender |
| `GREENROOM_GITHUB_TOKEN` | unset (Feedback page logs only) | Fly secret (PAT with `public_repo` scope) |
| `GREENROOM_GITHUB_REPO` | unset (defaults to `adamklie/greenroom`) | optional override |
| `GREENROOM_R2_PRESIGN_TTL_SECONDS` | n/a | optional; defaults to 3600 (1h) |

### The dual R2 secret naming

Each R2 credential is set **twice** — once unprefixed (`R2_*`) and once prefixed (`GREENROOM_R2_*`):

- **Unprefixed** (`R2_ACCESS_KEY_ID`, `R2_BUCKET`, ...) — read by `infra/litestream.yml` and `infra/entrypoint.sh` via shell substitution.
- **Prefixed** (`GREENROOM_R2_ACCESS_KEY_ID`, ...) — read by Pydantic's `env_prefix="GREENROOM_"` for `Settings.r2_*` in the FastAPI app.

Dual-setting is simpler than adding `AliasChoices` to every R2 field. The values are identical.

---

## Litestream behavior

`infra/litestream.yml` is a template — values interpolate from env vars at container runtime. `infra/entrypoint.sh` checks for `R2_ACCESS_KEY_ID + R2_SECRET_ACCESS_KEY + R2_BUCKET`:

- **All three present** → restore from R2 if no local DB, then `litestream replicate -exec uvicorn` so every WAL write streams to R2.
- **Any missing** → uvicorn runs directly with no replication.

DB backups go to a **separate** R2 bucket from media (`R2_DB_BACKUP_BUCKET` = `greenroom-1-db-backups`). Keeping them apart prevents an `rclone copy` of the media tree from clobbering DB snapshots and lets a media-only API token be issued for bulk uploads.

Retention: 30 days (`720h` in `litestream.yml`).

---

## First-deploy runbook

This is what was actually run for the initial `greenroom-1` deployment. Keep it as a reference for future deploys (re-region, disaster recovery, etc.).

### 1. One-time setup

```bash
fly apps create greenroom-1
fly volumes create data --app greenroom-1 --region lax --size 3
```

Region note: Fly removed `sea` (Seattle). For West Coast US, use `lax`.

### 2. Set Fly secrets

You need: an R2 account (Cloudflare), API tokens for an R2 user with object-read/write scope on the media + db-backup buckets, a Resend API key, a GitHub PAT (for the Feedback feature), and a fresh JWT signing secret.

Export the R2/Resend values into your shell first (typically via `~/.zshrc`), then:

```bash
AUTH_SECRET=$(openssl rand -hex 32)

fly secrets set -a greenroom-1 \
    R2_ACCESS_KEY_ID="$GREENROOM_R2_ACCESS_KEY_ID" \
    R2_SECRET_ACCESS_KEY="$GREENROOM_R2_SECRET_ACCESS_KEY" \
    R2_BUCKET="greenroom-1-media" \
    R2_DB_BACKUP_BUCKET="greenroom-1-db-backups" \
    R2_ACCOUNT_ID="9a19e3fc1679ae3ab01e97284b68d421" \
    GREENROOM_R2_ACCESS_KEY_ID="$GREENROOM_R2_ACCESS_KEY_ID" \
    GREENROOM_R2_SECRET_ACCESS_KEY="$GREENROOM_R2_SECRET_ACCESS_KEY" \
    GREENROOM_R2_ENDPOINT_URL="$GREENROOM_R2_ENDPOINT_URL" \
    GREENROOM_R2_BUCKET="greenroom-1-media" \
    GREENROOM_RESEND_API_KEY="$GREENROOM_RESEND_API_KEY" \
    GREENROOM_GITHUB_TOKEN="$GITHUB_TOKEN" \
    GREENROOM_AUTH_SECRET="$AUTH_SECRET" \
    GREENROOM_PUBLIC_URL="https://greenroom-1.fly.dev" \
    GREENROOM_ALLOWED_ORIGINS="https://greenroom-1.fly.dev"
```

Verify with `fly secrets list -a greenroom-1` — should show 13 keys. Don't use `--reveal`; the digest column is enough to detect "did this set?" (identical digests for distinct keys = both are the same value, usually a sign of an empty string).

### 3. Deploy

```bash
fly deploy -a greenroom-1
fly logs -a greenroom-1
```

Watch for `[entrypoint] starting litestream replicate + uvicorn` and `INFO: Application startup complete`. First boot creates the SQLite file fresh, runs Alembic migrations, then idles.

### 4. Create the first admin

`fly ssh console` over Fly's WireGuard tunnel is sometimes flaky on macOS (you'll see `tls: first record does not look like a TLS handshake`). Use `fly machine exec` as the reliable fallback:

```bash
# Find the machine ID first
fly status -a greenroom-1
# Then:
fly machine exec <machine-id> -a greenroom-1 \
  "sh -c 'cd /app/backend && python scripts/create_admin.py aklie@ucsd.edu'"
```

### 5. Verify

```bash
curl https://greenroom-1.fly.dev/api/health
# {"status":"ok","app":"greenroom","version":"0.2.0"}

curl -I https://greenroom-1.fly.dev/
# 200, content-type: text/html

curl -X POST https://greenroom-1.fly.dev/api/auth/request \
     -H 'Content-Type: application/json' \
     -d '{"email":"aklie@ucsd.edu"}'
# {"ok":true,"message":"..."}
```

Then click the magic link in your inbox (or check Resend dashboard if it didn't arrive — sandbox sender only delivers to your Resend account's signup email).

---

## Resend sandbox vs verified domain

By default the deploy uses Resend's sandbox sender `onboarding@resend.dev`, which **only delivers to the email you registered the Resend account with**. Any other recipient gets silently dropped at Resend's end.

To send magic links to other people (bandmates), either:

1. **Verify a domain** in Resend (DNS records: SPF + DKIM + DMARC), then update `GREENROOM_RESEND_FROM_EMAIL` to `Greenroom <noreply@yourdomain>`. Recommended for >2 users.
2. **Use the sandbox sender** and have each user separately verify themselves at Resend (limited; not all plans support this).

For a quick test, you can text yourself the magic link from your own inbox to test the flow on a different account.

---

## Bulk media upload (initial cutover)

Use `rclone` to push the iCloud vault to R2. This is a one-time operation; subsequent uploads happen through the app.

```bash
brew install rclone

# Configure the remote (writes ~/.config/rclone/rclone.conf chmod 600)
rclone config create greenroom-r2 s3 \
  provider Cloudflare \
  access_key_id "$GREENROOM_R2_ACCESS_KEY_ID" \
  secret_access_key "$GREENROOM_R2_SECRET_ACCESS_KEY" \
  endpoint "$GREENROOM_R2_ENDPOINT_URL" \
  acl private

# Scoped R2 tokens can't CreateBucket; turn off the existence check
rclone config update greenroom-r2 no_check_bucket true

# Upload (use copy, not sync — sync would delete files from R2)
rclone copy \
  "$HOME/Library/Mobile Documents/com~apple~CloudDocs/greenroom/files" \
  greenroom-r2:greenroom-1-media/files \
  --progress \
  --transfers 8 \
  --checkers 16 \
  --s3-chunk-size 64M \
  --s3-upload-concurrency 4 \
  --retries 5 --low-level-retries 10 \
  --stats 30s \
  --log-file ~/greenroom-r2-upload.log
```

For 33 GB on residential upstream this takes 1–3 hours. Run with `caffeinate -i -w $(pgrep -f "rclone copy")` in a second terminal to keep your Mac awake.

Resumable: re-running the same command skips already-uploaded objects.

---

## DB cutover (initial migration of local data to prod)

If you start with empty prod (you should, on first deploy) and want to push your local SQLite up:

```bash
# Take a clean snapshot (safe with active writers)
SNAP=/tmp/greenroom-snapshot.db
sqlite3 ~/code/greenroom/greenroom.db ".backup '$SNAP'"

# Push to R2 (any bucket; we use the db-backups one's `cutover/` prefix)
rclone copyto "$SNAP" greenroom-r2:greenroom-1-db-backups/cutover/snap.db

# Pull onto the Fly machine via the in-container boto3
fly machine exec <machine-id> -a greenroom-1 "python3 -c \"
import boto3, os
s3 = boto3.client('s3',
    endpoint_url=os.environ['GREENROOM_R2_ENDPOINT_URL'],
    aws_access_key_id=os.environ['GREENROOM_R2_ACCESS_KEY_ID'],
    aws_secret_access_key=os.environ['GREENROOM_R2_SECRET_ACCESS_KEY'],
    region_name='auto')
s3.download_file('greenroom-1-db-backups', 'cutover/snap.db', '/data/greenroom.db.new')
print('downloaded')
\""

# Verify byte size matches, then swap atomically (delete stale wal/shm in the SAME exec)
fly machine exec <machine-id> -a greenroom-1 "sh -c '
  cp -p /data/greenroom.db /data/greenroom.db.empty-prod-backup &&
  mv /data/greenroom.db.new /data/greenroom.db.staged &&
  mv /data/greenroom.db /data/greenroom.db.old &&
  mv /data/greenroom.db.staged /data/greenroom.db &&
  rm -f /data/greenroom.db-wal /data/greenroom.db-shm
'"

# Restart to pick up the swap
fly machine restart <machine-id> -a greenroom-1

# Re-create admins (the snapshot's users table is local; local has 0 users)
fly machine exec <machine-id> -a greenroom-1 \
  "sh -c 'cd /app/backend && python scripts/create_admin.py aklie@ucsd.edu'"
```

The wal/shm cleanup in the swap exec is critical. Without it, SQLite tries to "checkpoint" the old WAL into the new DB file and corrupts it. The boot-time integrity check (`infra/entrypoint.sh`) catches this and auto-recovers from R2, but you save a deploy cycle by cleaning up at swap time.

---

## Ongoing operations

### Deploying a code change

```bash
cd ~/code/greenroom
git pull origin main
fly deploy -a greenroom-1
```

You only need this if a code/Dockerfile/infra change landed. Docs-only commits don't require a deploy.

### Rolling back a bad deploy

```bash
fly releases -a greenroom-1
fly deploy --image registry.fly.io/greenroom-1:deployment-<old-id> -a greenroom-1
```

DB rollback is independent — see [ARCHITECTURE.md](ARCHITECTURE.md) for Litestream point-in-time restore.

### Adding a new user

```bash
fly machine exec <machine-id> -a greenroom-1 \
  "sh -c 'cd /app/backend && python scripts/create_admin.py <email>'"
```

There is no in-app invite UI yet.

### Cleaning up DB orphans

If any audio_files rows reference files missing from R2:

```bash
# List first
fly machine exec <machine-id> -a greenroom-1 \
  "sh -c 'cd /app/backend && python scripts/cleanup_orphan_audio_files.py --list-only'"

# Soft-delete (recoverable)
fly machine exec <machine-id> -a greenroom-1 \
  "sh -c 'cd /app/backend && python scripts/cleanup_orphan_audio_files.py --yes'"

# Or permanently delete
fly machine exec <machine-id> -a greenroom-1 \
  "sh -c 'cd /app/backend && python scripts/cleanup_orphan_audio_files.py --hard --yes'"
```

The script uses a single R2 `list_objects_v2` call (not per-row HEADs), so it fits within Fly's exec timeout even for 600+ candidates.

---

## R2 CORS — required for direct browser → R2 multipart uploads

The Process page uploads large GoPro videos straight from the browser to R2 using presigned multipart PUT URLs (saves the laptop→Fly→R2 double-hop). For that to work, R2 must allow PUTs from the app origin and must expose the `ETag` response header to JS — both are CORS settings.

This is a Cloudflare dashboard config, not an env var. Apply it once per bucket:

1. Cloudflare dashboard → R2 → `greenroom-1-media` → **Settings** → **CORS Policy** → **Add Policy**
2. Paste:

```json
[
  {
    "AllowedOrigins": ["https://greenroom-1.fly.dev", "http://localhost:5173"],
    "AllowedMethods": ["PUT", "POST", "GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": ["ETag"],
    "MaxAgeSeconds": 3600
  }
]
```

3. Save. Takes effect within ~1 minute.

Without `ExposeHeaders: ["ETag"]` the browser strips ETag from the PUT response and the upload state machine errors out with `no ETag in R2 response`. Without `AllowedOrigins` matching the page origin the browser blocks the PUT before it even reaches R2.

The legacy single-shot `/api/gopro/upload-raw` endpoint doesn't need CORS — it streams through Fly first.

---

## Troubleshooting

**Image build fails with `ModuleNotFoundError: app` inside the container** — Dockerfile must `COPY backend/` **before** `pip install -e ./backend`. Installing first against just `pyproject.toml` leaves an empty package (setuptools `packages.find` ran when `app/` didn't exist yet).

**Litestream restore fails with "cannot restore, output path already exists"** — the `-if-replica-exists` flag handles "no backup in bucket" but not "local DB already there." The entrypoint guards this with `if [ ! -f "$DB_PATH" ]; then restore; fi`.

**Litestream/uvicorn boot loop with "database disk image is malformed"** — usually stale `.db-wal` / `.db-shm` files from a previous process trying to checkpoint into a swapped-in `.db`. The entrypoint integrity check now auto-detects and recovers from R2; if it can't (no replica), you'll need to push a fresh snapshot via the DB cutover steps above.

**`fly ssh console` fails with "tls: first record does not look like a TLS handshake"** — known WireGuard tunnel issue on macOS. Use `fly machine exec` instead.

**`fly machine exec` times out** — exec has a short header timeout. Heavy work (e.g. per-row R2 HEAD requests) won't finish in time. Optimize the script (single `list_objects_v2`) or use `fly ssh console` if available.

**rclone fails with `operation error S3: CreateBucket, AccessDenied`** — scoped R2 tokens can't create buckets. Add `no_check_bucket = true` to the remote config (or `--s3-no-check-bucket` flag).

**rclone fails overnight with `RequestTimeTooSkewed`** — Mac slept and the system clock drifted past S3's 15-minute signature tolerance. Run `caffeinate -i -w $(pgrep -f "rclone copy")` to keep it awake.

**Magic link email never arrives** — Resend dashboard at <https://resend.com/emails> shows the actual status. Sandbox sender only delivers to your Resend account email. To send elsewhere, verify a domain (see "Resend sandbox vs verified domain" above).

**Feedback page silent-fails to file issues** — `GREENROOM_GITHUB_TOKEN` isn't set. Generate a PAT at <https://github.com/settings/tokens> with `public_repo` scope and `fly secrets set GREENROOM_GITHUB_TOKEN=...` to fix.

**SPA serves but `/api/*` returns 404** — static mount happens AFTER router registration in `main.py`. If a `/` mount lands first, it shadows everything.

**Hard refresh on `/sessions` (or any SPA route) returns 404** — the StaticFiles mount needs `html=True` so unknown paths fall back to `index.html`.

**Process page video upload fails with "no ETag in R2 response (check bucket CORS config)"** — the R2 bucket is missing `ExposeHeaders: ["ETag"]` (or CORS isn't configured at all). See "R2 CORS" above for the JSON policy.

**Process page video upload fails with `CORS policy: No 'Access-Control-Allow-Origin' header`** — bucket CORS doesn't list the page origin. Add `https://greenroom-1.fly.dev` (and `http://localhost:5173` for dev) to `AllowedOrigins`. See "R2 CORS" above.

---

## Files

| Path | Purpose |
|---|---|
| `Dockerfile` | Multi-stage build (node → python-slim runtime) |
| `.dockerignore` | Keeps build context small; excludes live DB |
| `docker-compose.yml` | Local parity stack |
| `fly.toml` | Fly app config (app name, region, mounts, non-secret env) |
| `infra/entrypoint.sh` | Litestream wrapper around uvicorn + integrity check + wal/shm cleanup |
| `infra/litestream.yml` | Replication config template (R2) |
| `backend/app/main.py` | Static mount + env-driven CORS |
| `backend/app/config.py` | All `GREENROOM_*` settings |
| `.github/workflows/test.yml` | CI: pytest + frontend build on every push/PR |
