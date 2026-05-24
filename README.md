# Greenroom

[![Test](https://github.com/adamklie/greenroom/actions/workflows/test.yml/badge.svg)](https://github.com/adamklie/greenroom/actions/workflows/test.yml)

The badge above reflects the latest `Test` workflow run on `main` — backend pytest plus frontend `tsc && vite build`, both run on every push and on PRs to `main`. Green means the 60-test backend suite passed and the TypeScript build had no type errors at that revision.

A private app for tracking your band's songs, recordings, and practice sessions. Think of it as a digital songbook + recording library + practice diary.

**Production:** <https://greenroom-1.fly.dev> (magic-link sign-in)
**Code:** this repo. Deployed on Fly.io (LAX) with Cloudflare R2 for media storage.

## What you can do

- **Library** — Every audio/video clip in one searchable place. Filter by source, role, song. Inline playback streams from cloud storage with full scrub support.
- **Songs (Covers / Originals / Ideas)** — Status-tracked catalog with versioned lyrics, key/tempo/tuning, tags.
- **Sessions** — Practice sessions grouped by date. Each session expands into its takes, rateable across 7 dimensions (overall, vocals, guitar, drums, tone, timing, energy).
- **Setlists** — Build ordered song collections for performances.
- **Process** — Cut a long practice video into per-song clips (local dev only — see DEPLOYMENT).
- **Tabs** — Upload Guitar Pro files (`.gp`–`.gp7`) and play them inline via alphaTab.
- **Progress** — Practice frequency, rating trends, skill radar, status funnel.
- **Settings → Export JSON** — Download every annotation as a portable JSON file.

## Tech Stack

- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Storage:** Cloudflare R2 (media) + Fly volume (SQLite, replicated to R2 via Litestream)
- **Auth:** Magic-link with JWT cookies. Three roles: viewer / editor / admin
- **Email:** Resend (transactional)
- **Hosting:** Fly.io, single container, ~$5–7/month total

## Docs

Start at the index: [docs/README.md](docs/README.md).

| Doc | What's in it |
|---|---|
| [docs/README.md](docs/README.md) | Index — points at the right page for users, operators, and hackers |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | What each page does, common workflows, backups, roles |
| [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) | 10-min walkthrough for showing the app to a new user |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System map, request flows, boot sequence, storage layout, auth model |
| [docs/SCHEMAS.md](docs/SCHEMAS.md) | DB schema, SQLAlchemy model reference |
| [docs/DATA_INGESTION.md](docs/DATA_INGESTION.md) | Ingestion scripts and data flow |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Fly + R2 + Resend setup, secrets, runbook |
| [docs/MIGRATIONS.md](docs/MIGRATIONS.md) | Alembic conventions, applying schema changes |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) | Principles, PR cycle, Explore → Plan → Code → Test |
| [docs/STYLE.md](docs/STYLE.md) | Style guide for writing docs in this repo |
| [docs/AUDIOFILE_UNIFICATION.md](docs/AUDIOFILE_UNIFICATION.md) | Ongoing refactor: Take → AudioFile |
| [docs/REMOVED.md](docs/REMOVED.md) | Features cut during simplification and why |

## Quick Start — Local Dev

### Prerequisites

- Python 3.11+
- Node.js 18+
- ffmpeg (for trim / extract-audio)

### Setup

```bash
git clone https://github.com/adamklie/greenroom ~/code/greenroom
cd ~/code/greenroom

# Backend deps
cd backend && pip install -e ".[dev]" && cd ..

# Frontend deps
cd frontend && npm install && cd ..

# Bootstrap from local vault (audio + practice sessions)
make bootstrap
```

### Run

```bash
make dev   # runs backend + frontend concurrently
```

Then open **<http://localhost:5173>**.

In local dev, `AUTH_REQUIRED=false` by default — no login screen. Set `GREENROOM_AUTH_REQUIRED=true` to test the magic-link flow locally.

### Config

| Env var | Default | Purpose |
|---|---|---|
| `GREENROOM_DB_PATH` | `<repo>/greenroom.db` | SQLite location |
| `GREENROOM_VAULT_DIR` | `~/Library/Mobile Documents/com~apple~CloudDocs/greenroom` | Local vault for audio/video |
| `GREENROOM_MEDIA_BACKEND` | `local` | `local` for filesystem, `r2` for Cloudflare R2 |
| `GREENROOM_AUTH_REQUIRED` | `false` | Toggle magic-link auth in dev |
| `GREENROOM_AUTH_SECRET` | (must set in prod) | JWT signing secret |
| `GREENROOM_PUBLIC_URL` | `http://localhost:5173` | Base URL for magic links |

Production env vars live in `fly secrets` — see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Project Layout

```
backend/app/
  main.py           # FastAPI app + route registration + lifespan
  routers/          # API handlers (one file per resource)
  models/           # SQLAlchemy ORM
  services/
    vault.py        # Storage abstraction (LocalVaultBackend + CloudVaultBackend)
    backup.py       # DB backups + JSON export
    autosync.py     # File reorganization (local-only)
  auth/             # Magic-link + JWT + role gating
  alembic/          # Schema migrations
backend/scripts/    # CLI utilities (create_admin, bootstrap, ...)
backend/tests/      # pytest suite (55 tests at last commit)

frontend/src/
  pages/            # Top-level SPA pages (one per sidebar item)
  api/client.ts     # Typed API client
  components/       # Shared UI

infra/
  entrypoint.sh     # Container boot script (litestream restore + replicate + uvicorn)
  litestream.yml    # WAL → R2 replication config

Dockerfile          # Two-stage: node frontend build, python runtime
docker-compose.yml  # Local container parity
fly.toml            # Fly app config
Makefile            # Common targets: dev, test, lint, bootstrap, deploy
docs/               # Architecture, user guide, deployment, demo script
```

## Key API endpoints

The backend exposes a REST API. All routes require auth in prod (viewer+ for reads, editor+ for writes).

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Liveness check (unauthenticated) |
| `POST /api/auth/request` | Send magic-link email |
| `GET /api/auth/exchange?token=…` | Exchange magic token for JWT cookie |
| `GET /api/dashboard` | Stats + recent additions |
| `GET /api/songs` / `PATCH /api/songs/{id}` | Song CRUD with status / lyrics / tags |
| `GET /api/audio-files` / `PATCH /api/audio-files/{id}` | Library CRUD + rating |
| `GET /api/sessions` / `GET /api/sessions/{id}` | Practice sessions + their audio |
| `GET /api/setlists` | Setlist CRUD |
| `GET /api/tabs` | Guitar Pro attachments |
| `GET /api/media/audio/{id}` | 307 redirect to presigned R2 URL (cloud) or Range stream (local) |
| `POST /api/upload` | Drag-drop ingest into vault |
| `POST /api/backup/create` | Create DB snapshot |
| `GET /api/backup/export-download` | Stream all annotations as JSON |
| `GET /api/analytics/*` | Practice frequency, rating trends |

Full API surface: see `backend/app/routers/`.

## License

MIT
