# Architecture

How Greenroom is wired together. The goal here is to answer "what happens
when X" without spelunking the code. For deployment-specific runbook detail
(secrets, first-deploy steps, troubleshooting), see
[`DEPLOYMENT.md`](DEPLOYMENT.md). For the user-facing tour, see
[`USER_GUIDE.md`](USER_GUIDE.md).

---

## 1. System map

One Fly machine in `lax` runs a single Python process (uvicorn → FastAPI)
that serves both the JSON API at `/api/*` and the built React SPA at `/`.
A Fly volume mounted at `/data` holds the live SQLite database and any
local-mode vault state. Litestream — wrapped around uvicorn by
`infra/entrypoint.sh` — streams every SQLite WAL change to a Cloudflare R2
bucket. Media (audio + video) lives in a separate R2 bucket and is served
to browsers via short-lived presigned URLs. Outbound email goes to Resend
over HTTPS.

```
                ┌──────────────────────────────┐
                │ Browser (SPA in greenroom-1) │
                └───────┬──────────────────┬───┘
                        │ /api/*           │ 307 redirect to
                        │ /                │ presigned R2 URL
                        ▼                  │
        ┌────────────────────────────┐     │
        │ Fly machine (lax, 1 GB)    │     │
        │   uvicorn + FastAPI        │     │
        │   StaticFiles → SPA        │     │
        └──┬──────────┬──────────────┘     │
           │          │                    │
           │ reads/   │ Litestream         │
           │ writes   │ replicates WAL     │
           ▼          ▼                    ▼
   ┌──────────────┐   ┌────────────────────────────┐
   │ Fly volume   │   │ Cloudflare R2              │
   │ /data        │   │  ├─ ${R2_BUCKET}           │
   │  greenroom.db│   │  │   files/AF…ext  (media) │
   │  vault/      │   │  └─ ${R2_DB_BACKUP_BUCKET} │
   └──────────────┘   │      greenroom-db/…  (WAL) │
                      └────────────────────────────┘
                                ▲
                                │ HTTPS
                                │
                       ┌────────┴────────┐
                       │ Resend (email)  │
                       └─────────────────┘
```

Roughly seven boxes: browser, Fly machine, Fly volume, two R2 buckets,
Litestream (logically), Resend.

---

## 2. Request flow walkthroughs

### 2a. Page load

```
Browser                     Fly machine                          R2/DB
   │                             │
   │ GET https://greenroom-1.fly.dev/
   ├────────────────────────────►│
   │                             │  StaticFiles mount in app/main.py
   │                             │  resolves /  → /app/static/index.html
   │ 200 index.html              │  (html=True falls back here for any
   │◄────────────────────────────┤   unknown sub-path so /sessions etc.
   │                             │   work on hard refresh)
   │
   │ GET /assets/*.{js,css}      │
   ├────────────────────────────►│  StaticFiles
   │ 200 hashed bundle           │
   │◄────────────────────────────┤
   │
   │ React mounts. useCurrentUser() fires:
   │ GET /api/auth/me            │
   │ Cookie: greenroom_session=… │
   ├────────────────────────────►│  auth/router.py /me
   │                             │  → decode_token() → users row lookup
   │                             │                     ├─► /data/greenroom.db
   │ 200 {id, email, role}       │                     │
   │◄────────────────────────────┤
   │
   │ App.tsx now has a user. NavLink-driven pages each fire their own
   │ GET /api/dashboard, /api/audio_files, etc. — every route Depends()
   │ on require_viewer (or higher), which re-validates the cookie.
```

If `/api/auth/me` returns 401, the SPA renders `<Login />` instead of
`<AppShell />` (see `frontend/src/App.tsx`).

### 2b. Magic-link login

```
Browser                     Fly machine                Resend         User inbox
   │                             │                       │
   │ POST /api/auth/request      │
   │ {email: "you@…"}            │
   ├────────────────────────────►│  auth/router.py: look up users row
   │                             │  if found, insert magic_tokens row
   │                             │  (sha256 of 32-byte urlsafe token,
   │                             │   expires_at = now + 15 min)
   │                             │
   │                             │  POST https://api.resend.com/emails
   │                             ├──────────────────────►│
   │                             │  {from, to, subject:  │
   │                             │   "Sign in to         │  delivers
   │                             │   Greenroom", html}   │  ┌────────►
   │ 200 {ok:true, message: …}   │                       │
   │◄────────────────────────────┤
   │                             │
   │   (response is identical whether or not the email was registered —
   │    anti-enumeration. Resend HTTP failures are logged, not raised.)
   │
   │ User clicks link in inbox:
   │ GET /api/auth/exchange?token=raw_token
   ├────────────────────────────►│  hash the token, look up magic_tokens
   │                             │  row, verify: not used, not expired
   │                             │  → mark used_at = now
   │                             │  → encode_token(user_id, role)  (JWT)
   │                             │  → Set-Cookie: greenroom_session=…;
   │                             │       HttpOnly; SameSite=Lax;
   │                             │       Secure; Max-Age=604800 (7d)
   │ 303 See Other  →  /         │
   │◄────────────────────────────┤
   │
   │ GET /  (now with the cookie) — falls into the Page-load flow above.
```

Magic-link TTL: 15 minutes, single-use (`used_at` enforces this). JWT
cookie TTL: 7 days, HS256-signed with `GREENROOM_AUTH_SECRET`. See
`backend/app/auth/router.py` and `backend/app/auth/jwt.py`.

### 2c. Playing media (cloud backend)

```
Browser                  Fly machine                              R2
   │                          │
   │ <audio src="/api/media/audio/4711">
   │ GET /api/media/audio/4711                                      │
   │ Cookie: greenroom_session=…                                    │
   ├─────────────────────────►│
   │                          │ media.py: require_viewer
   │                          │ → db.query(AudioFile).get(4711)
   │                          │ → row has identifier="AFE9C7481F",
   │                          │       file_type="mp3"
   │                          │ → backend = get_backend()
   │                          │   (CloudVaultBackend, since
   │                          │    GREENROOM_MEDIA_BACKEND=r2)
   │                          │ → backend.url_for(af) presigns:
   │                          │       GET files/AFE9C7481F.mp3
   │                          │       in ${R2_BUCKET}, TTL=1h
   │ 307 Temporary Redirect   │
   │ Location: https://${R2}.r2.cloudflarestorage.com/files/AFE9…   │
   │◄─────────────────────────┤
   │
   │ Browser follows the 307 directly to R2. The Fly machine never
   │ proxies the audio bytes — important when memory is 1 GB and the
   │ media tree is ~33 GB.
   │ GET (presigned URL, with Range: bytes=0-)                      │
   ├──────────────────────────────────────────────────────────────►│
   │ 206 Partial Content, Accept-Ranges: bytes                      │
   │◄──────────────────────────────────────────────────────────────│
   │ (further Range requests for scrub/seek go straight to R2)
```

Local-backend path (`MEDIA_BACKEND=local`) doesn't redirect — `url_for`
returns `None` and `media.py` falls through to `_serve_with_range`, which
streams the file directly with 206 Partial Content support. See
`backend/app/routers/media.py` lines 112–127.

### 2d. Saving a rating

```
Browser              Fly machine                         /data        R2 (db backups)
   │                      │                                │
   │ PATCH /api/audio_files/4711                          │
   │ {rating_overall: 4.5}                                │
   │ Cookie: greenroom_session=…                          │
   ├─────────────────────►│
   │                      │ audio_files.py:
   │                      │   require_editor → cookie decoded,
   │                      │   role rank ≥ 2; raise 403 otherwise
   │                      │ af = db.query(AudioFile).get(4711)
   │                      │ for field,val in payload: setattr(af, field, val)
   │                      │ db.commit()                    │
   │                      │ → SQLite append to greenroom.db-wal
   │                      │                                │
   │                      │                                │ Litestream tail
   │                      │                                │ picks up the WAL
   │                      │                                │ frame and PUTs
   │                      │                                │ it to R2 within
   │                      │                                │ ~1s (default
   │                      │                                │  sync interval).
   │                      │                                ├──────────────►│
   │ 200 AudioFileRead    │                                │
   │◄─────────────────────┤
```

Auth gating: `require_editor` lives in `backend/app/auth/deps.py` and is
attached as a `Depends()` on every PATCH/POST/DELETE handler. Read routes
use `require_viewer`. The dev bypass (`GREENROOM_AUTH_REQUIRED=false`)
short-circuits the check by returning a synthetic admin User; production
has it set to `true`.

---

## 3. Boot sequence

`infra/entrypoint.sh` is the container's `CMD`. What happens, in order,
when a Fly machine starts (cloud path — both R2 creds present):

1. **Set env defaults.** `PORT` → 8080, `GREENROOM_DB_PATH` → `/data/greenroom.db`.
   `mkdir -p /data` so SQLite + Litestream both have a directory to write into
   on first boot.
2. **Check for R2 creds.** If `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`,
   and `R2_BUCKET` are all set, the script takes the cloud branch.
   Otherwise it execs uvicorn directly with no Litestream replication
   (the compose / local-parity path).
3. **Local DB integrity gate.** If `/data/greenroom.db` exists:
   - Run `PRAGMA integrity_check` via inline `python3 -c …`.
   - **ok** → remove any stale `*-wal` / `*-shm` siblings (`mv` of a
     `.db` under an active SQLite process can leave these behind; if
     a fresh process tries to attach, the leftover WAL can poison the
     read).
   - **not ok** → move the file aside as `greenroom.db.corrupt-<ts>`,
     remove the WAL/SHM, fall through to step 4.
4. **Restore from R2 if missing.** When `/data/greenroom.db` doesn't
   exist (fresh volume, or step 3 moved it aside), run
   `litestream restore -if-replica-exists -config /etc/litestream.yml
   /data/greenroom.db`. The `-if-replica-exists` flag makes this a no-op
   on a brand-new app (no replica yet); otherwise it pulls down the
   latest generation from `${R2_DB_BACKUP_BUCKET}/greenroom-db/`.
5. **Hand off to Litestream + uvicorn.**
   `exec litestream replicate -config /etc/litestream.yml -exec
   "uvicorn app.main:app --host 0.0.0.0 --port 8080"`. Litestream is now
   the parent process; uvicorn is its child. WAL frames replicate to
   R2 every ~1 second.
6. **FastAPI lifespan.** Inside `app/main.py`, the lifespan handler runs
   `command.upgrade(cfg, "head")` against Alembic to apply any pending
   migrations (in `backend/alembic/versions/`). Then it kicks off a
   background thread that calls `services/backup.backup_database()` to
   drop a timestamped copy into `vault_dir/backups/`.
7. **Routes served.** uvicorn binds `0.0.0.0:8080`; Fly's edge proxy
   forwards `https://greenroom-1.fly.dev` traffic in. The static SPA
   mount is registered last so `/api/*` always wins.

For the local / compose case, steps 3–5 are replaced by a single
`exec uvicorn …` — no Litestream, no restore, no integrity check.

---

## 4. Code layout

Top-level tree, one line per directory/file that matters:

```
backend/app/main.py             — FastAPI app + router registration + lifespan (Alembic upgrade, background backup)
backend/app/config.py           — Pydantic Settings (env_prefix=GREENROOM_); reads .env or env vars
backend/app/database.py         — SQLAlchemy engine, SessionLocal, get_db() dep
backend/app/routers/            — endpoint handlers, one file per resource (audio_files, songs, sessions, media, …)
backend/app/models/             — SQLAlchemy ORM (audio_file, song, session, take, setlist, song_tab, user, …)
backend/app/services/           — vault (storage backends), email, file_manager, autosync, bootstrap, backup
backend/app/auth/               — magic-link issue/exchange (router.py), JWT (jwt.py), role gating (deps.py)
backend/app/schemas/            — Pydantic request/response models
backend/alembic/versions/       — schema migrations (two so far: baseline + users/magic_tokens)
backend/scripts/                — CLI utilities: create_admin, stamp_baseline, migrate_to_vault, drop_simplified_tables, restore_song_annotations, bootstrap, benchmark
backend/tests/                  — pytest suite (55 tests across auth, vault, media redirect, integration, smoke, cloud-mode safety)
frontend/src/App.tsx            — sidebar shell, route table, login gate
frontend/src/pages/             — top-level pages: Dashboard, Library, Songs, Sessions, Progress, ProcessSession, SetlistBuilder, Import, Feedback, Schemas, Settings
frontend/src/api/client.ts      — typed fetch client used by every page
frontend/src/components/        — reusable UI (TabViewer for AlphaTab rendering)
frontend/src/auth/              — useCurrentUser hook, Login page, RoleGate
frontend/src/BackendHealth.tsx  — fixed-position banner; polls /api/health every 15s
infra/entrypoint.sh             — container boot script — read this when boot weirdness happens
infra/litestream.yml            — continuous WAL → R2 replication config (env-templated)
Dockerfile                      — two-stage: node:20-alpine builds the SPA, python:3.11-slim runs uvicorn
fly.toml                        — Fly app config (region lax, 1 GB VM, /data mount, non-secret env)
docker-compose.yml              — local-parity stack with bind mount instead of Fly volume
docs/DEPLOYMENT.md              — fly secrets + first-deploy runbook
docs/SCHEMAS.md                 — table-by-table SQLAlchemy reference
```

---

## 5. Storage layout

### `/data/greenroom.db` — Fly volume, 3 GB

SQLite file living on the Fly volume mount declared in `fly.toml`.
Current row counts (from the live DB at the time these docs were
written, queried with `sqlite3 greenroom.db 'SELECT COUNT(*) FROM …'`):

| Table | Rows |
|---|---|
| `audio_files` | 712 |
| `songs` | 226 |
| `practice_sessions` | 31 |
| `takes` | 363 |
| `tags` | 14 |
| `setlists` | 0 |
| `users` | (bootstrap with `scripts/create_admin.py`) |

Survives machine restarts because the volume is attached. Does **not**
survive volume loss — that's what Litestream is for.

### `/data/vault/backups/greenroom_*.db`

Snapshots written by `services/backup.backup_database()` on each app
startup (background thread in the lifespan handler). Rolling window of
`MAX_BACKUPS = 10` — older ones get pruned. These supplement, not
replace, Litestream — they're a "what did the schema/data look like at
boot N" sanity copy on the same volume.

### `${R2_BUCKET}` (media)

Cloudflare R2 bucket holding every audio + video file. Object keys
follow `files/{identifier}.{ext}` exactly, where `identifier` is the
10-char `AF…` ID generated by `models/audio_file.generate_identifier()`
(`"AF" + sha256(filename+timestamp)[:8].upper()`). This layout is
canonical — see `CloudVaultBackend._key()` in
`backend/app/services/vault.py`. Examples:

```
files/AF12AB34CD.m4a
files/AFE9C7481F.mp3
files/AF0023AC08.mp4
```

Browsers fetch from R2 directly via 1-hour presigned GET URLs (TTL
configurable via `GREENROOM_R2_PRESIGN_TTL_SECONDS`).

### `${R2_DB_BACKUP_BUCKET}` (Litestream WAL replicas)

Separate R2 bucket for Litestream output, under a `greenroom-db/`
prefix. Retention 30 days (`720h` in `infra/litestream.yml`). Holds
the WAL generation tree Litestream needs to reconstruct the DB at any
point inside the retention window. Kept apart from the media bucket so
(a) a stray `rclone sync` of media can't clobber DB backups,
(b) a media-only API token can be issued for bulk-upload scripts
without giving them DB access, (c) retention/versioning can differ per
bucket.

### Local-mode vault (dev)

When `GREENROOM_MEDIA_BACKEND=local` (the default for `./dev.sh`), media
lives on disk in the iCloud-synced vault rather than R2:

```
~/Library/Mobile Documents/com~apple~CloudDocs/greenroom/
├── files/
│   ├── AF12AB34CD.m4a
│   ├── AFE9C7481F.mp3
│   └── ...
├── backups/
│   └── greenroom_YYYYMMDD_HHMMSS.db  (rolling window of 10)
└── exports/
    └── annotations_latest.json
```

Why flat + identifier-named: the canonical path is fully derivable from
the DB (`identifier` + `file_type`). Restoring the DB is all you need
to regain access to every file. Import is idempotent — re-importing
the same file resolves to the same vault path. Apple's "Optimize Mac
Storage" can evict the local copy of files you haven't opened recently;
they're re-downloaded on demand.

### DB backup triggers (local mode)

Two paths kick a backup into `vault_dir/backups/`:

- **Auto (debounced):** every DB commit schedules a backup 30 seconds
  in the future (see `services/auto_backup.py`). A burst of writes
  collapses into a single backup.
- **Manual:** `POST /api/backup/create` (Settings page button).

The last 10 are kept; older are pruned. Because the vault is
iCloud-synced, every backup ends up in the cloud automatically. Cloud
deployments don't use this path — Litestream replicates the WAL
continuously to R2 (see above).

### Disaster recovery (local mode, new machine)

1. Sign into iCloud. Wait for `greenroom/` to sync down.
2. `git clone https://github.com/adamklie/greenroom ~/code/greenroom`.
3. Install deps (`make setup`).
4. Copy the newest DB backup into place:
   ```bash
   cp ~/Library/Mobile\ Documents/com~apple~CloudDocs/greenroom/backups/greenroom_*.db \
      ~/code/greenroom/backend/greenroom.db
   ```
   (pick the most recent by timestamp)
5. Start the app. Every `AudioFile` resolves against the vault.

---

## 6. Auth model

Three roles, ranked centrally in `backend/app/auth/deps.py`:

```python
_ROLE_RANK = {"viewer": 1, "editor": 2, "admin": 3}
```

| Role | Can do |
|---|---|
| `viewer` | All `GET` endpoints (read every resource, stream media). |
| `editor` | `viewer` + every mutation: POST/PATCH/DELETE on audio_files, songs, sessions, tags, setlists, tabs, options, upload, backup, trim, trash. |
| `admin` | `editor` + future user management. No admin-only routes wired yet. |

Routes opt in via FastAPI dependencies:

```python
@router.patch("/{audio_file_id}")
def update_audio_file(..., _user=Depends(require_editor)):
    ...
```

`require_viewer` / `require_editor` / `require_admin` are factory-built
by `_require_role()` and live in `auth/deps.py`. The dependency:

1. Reads the `greenroom_session` cookie.
2. `decode_token()` → JWT payload (HS256, `GREENROOM_AUTH_SECRET`).
3. Loads the User row by `payload["user_id"]`.
4. Raises **401** if no cookie / bad token / missing user.
5. Raises **403** if the user's role rank is below the required level.

The frontend turns 403 into a toast (see `ForbiddenToast` in `App.tsx`)
so viewers get a hint when they try an editor action.

**Magic-link TTL:** 15 minutes, single-use. Token is a 32-byte urlsafe
random string; only its sha256 is stored.

**JWT TTL:** 7 days. Cookie is `HttpOnly; SameSite=Lax; Secure`
(under HTTPS) and the JWT payload carries just `user_id`, `role`, `iat`,
`exp`.

**Dev bypass:** `GREENROOM_AUTH_REQUIRED=false` (the default in
local/dev) makes every gate return a synthetic admin user
(`id=0, email='dev@local', role='admin'`). Production has it set to
`true` via `fly.toml`.

### Adding a user

There is no signup flow — admin-invite-only. To add the first admin:

```bash
cd backend
python scripts/create_admin.py aklie@ucsd.edu
```

If the email already exists in `users`, its role is promoted to admin.
Otherwise the script inserts a new row. To add other users until the
admin UI lands, insert into `users` directly:

```sql
INSERT INTO users (email, role) VALUES ('teammate@example.com', 'editor');
```

### Stub emailer (dev)

While `GREENROOM_EMAIL_BACKEND=stub` (the default in dev), the magic
link is printed to the backend's stdout instead of sent. Copy the URL,
paste in the browser, you're in:

```
=== MAGIC LINK for aklie@ucsd.edu ===
http://localhost:5175/api/auth/exchange?token=...
=== expires in 15 minutes ===
```

The `resend` backend (cloud) wires the same `MagicLinkEmailer` interface
to Resend's HTTP API. See `backend/app/auth/email.py`.

---

## 7. Common operational gotchas

| Symptom | Cause | Fix |
|---|---|---|
| Persistent "Backend unreachable" banner | The banner used to probe `/api/dashboard`, which is auth-gated → returned 401 to unsigned-in visitors. | Now probes `/api/health` (commit `7f7b848`). If you see this banner with a valid login, the Fly machine actually is down — check `fly logs`. |
| Sessions vanish across deploys | `GREENROOM_AUTH_SECRET` is empty → `jwt.py` generates a new random key per process, invalidating every existing cookie on restart. | `fly secrets set GREENROOM_AUTH_SECRET=…` once. Already set in current prod. |
| `database disk image is malformed` after a swap | A DB swap (`mv`) under an active SQLite process leaves stale `-wal` / `-shm` files; a fresh process attaches them to the new `.db` and sees inconsistent state. | `infra/entrypoint.sh` integrity-checks the local DB on boot; if bad, moves it to `*.corrupt-<ts>` and restores from R2 (commit `3b3a6aa`). |
| Litestream restore on a fresh volume errors out | `litestream restore` without flags fails when no replica exists yet. | We pass `-if-replica-exists` — first boot becomes a no-op (commit `fe4281d`). |
| rclone bulk-upload says `CreateBucket: AccessDenied` | The scoped R2 API token can read/write objects in the existing bucket but isn't authorized to *create* buckets. rclone tries to verify by attempting a create. | Set `no_check_bucket = true` in the rclone remote config. |
| Magic link doesn't arrive | Resend account is on the sandbox sender (`onboarding@resend.dev`), which only delivers to the account owner's verified email. | Verify a custom domain in Resend, set `GREENROOM_RESEND_FROM_EMAIL` to a sender on that domain. Until then, only `aklie@ucsd.edu` will receive links. |
| `fly ssh sftp` hangs | Known flake with the WireGuard tunnel on macOS. | Use `fly machine exec <id> "<cmd>"` for one-shot commands, or `fly ssh console` for an interactive shell. For file transfer, use `fly machine exec` to upload via base64 or run boto3 against R2 directly. |
| First deploy: SPA serves but `/api/*` 404s | The static mount happens *after* router registration in `main.py`; if something is mounted at `/` earlier in the chain it shadows the API. | Keep the StaticFiles mount as the last call in `main.py`. |
| Hard refresh on a sub-route (e.g. `/sessions`) returns 404 instead of the SPA | `StaticFiles(...)` without `html=True` won't fall back to `index.html`. | Mount with `html=True` (already done). |
| Image build fails on `pip install -e ./backend` | Earlier split copied `pyproject.toml` before the `app/` source, so `setuptools.find_packages` saw nothing → empty package → `import app.*` broke from any non-`/app/backend` cwd. | Copy `backend/` *before* `pip install` (commit `762e012`). |

---

## See also

- [`USER_GUIDE.md`](USER_GUIDE.md) — what each page does, common workflows, what to do if something looks broken.
- [`DEPLOYMENT.md`](DEPLOYMENT.md) — fly secrets, first-deploy steps, image build details, rclone bulk-upload command.
- [`SCHEMAS.md`](SCHEMAS.md) — table-by-table SQLAlchemy reference.
