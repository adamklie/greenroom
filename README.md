# Greenroom

A song record-keeping tool for working musicians. Organize covers, originals, and ideas; attach recordings and Guitar Pro tabs to each song; rate practice takes; keep everything findable.

## Features

- **Dashboard** — Songs by type/status/project, recent activity, focus songs, data-protection actions
- **Songs (Covers / Originals / Ideas)** — Searchable catalog with status tracking (idea → rehearsed → polished → recorded → released), key/tempo/tuning, lyrics with version history, tags
- **Library** — Every audio file in one place; inline rating, song linking, trimming
- **Sessions** — Practice sessions and their takes, browsable by date, rateable in-browser
- **Setlists** — Build setlists per gig configuration; reorder; per-item duration totals
- **Tabs** — Upload Guitar Pro files (`.gp`, `.gp3`–`.gp7`, `.gpx`) and play them inline via alphaTab
- **Progress** — Practice frequency, rating trends, skill radar, status funnel
- **Triage** — Auto-detect new files on disk and classify them into the catalog
- **Import** — Drag-drop new audio/video; auto-extracts audio from video uploads
- **Sync** — One-button "After Practice" / "Weekly" snapshots of annotations + DB to the iCloud vault
- **Process** — Cut a long video (GoPro practice, etc.) into per-song clips

## Tech Stack

- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Media:** HTTP `Range`-aware streaming for audio/video scrubbing

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+

### Recommended layout

- Repo (code + live DB): `~/code/greenroom` — **not in iCloud**, backed up via GitHub
- Vault (audio/video files, DB backups, annotation exports): `~/Library/Mobile Documents/com~apple~CloudDocs/greenroom/` — auto-created on first run, iCloud-synced

See [docs/STORAGE.md](docs/STORAGE.md) for the full picture.

### Setup

```bash
# Clone to ~/code/greenroom (outside iCloud)
git clone https://github.com/adamklie/greenroom ~/code/greenroom
cd ~/code/greenroom

# Install backend dependencies
cd backend && pip install -e ".[dev]"

# Install frontend dependencies
cd ../frontend && npm install
```

### Run

```bash
# Terminal 1: Backend API
make backend

# Terminal 2: Frontend dev server
make frontend
```

Open **http://localhost:5173**

### Configuration

| Env var | Default | Purpose |
|---|---|---|
| `GREENROOM_VAULT_DIR` | `~/Library/Mobile Documents/com~apple~CloudDocs/greenroom` | iCloud vault root |
| `GREENROOM_MUSIC_DIR` | parent of repo | Legacy source-file resolution (used while migrating to the vault) |
| `GREENROOM_DB_PATH` | `<repo>/greenroom.db` | Live DB |

Set these in a `.env` file at the repo root or export them before running.

## How It Works

Files you drag into Greenroom (from `~/Downloads`, phone exports, etc.) are copied into the vault as `{identifier}.{ext}` — a flat directory where every file is named by its DB identifier (e.g. `AF12AB34CD.m4a`). Path resolution goes through `backend/app/services/vault.py`; no code infers location from song metadata. The DB carries the annotations (ratings, tags, lyrics, notes); the vault carries the bytes plus rolling DB backups. See [docs/STORAGE.md](docs/STORAGE.md).

## Project Structure

```
greenroom/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app
│   │   ├── config.py        # Settings (vault dir, music dir, DB path)
│   │   ├── database.py      # SQLAlchemy setup
│   │   ├── models/          # ORM models (Song, PracticeSession, Take, AudioFile, ...)
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── routers/         # API route handlers
│   │   └── services/        # Vault, file_manager, bootstrap, autosync, backup, ...
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Shell with sidebar navigation
│   │   ├── api/client.ts    # Typed API client
│   │   └── pages/           # Dashboard, Songs, Sessions, Library, Setlists, ...
│   └── package.json
├── scripts/                 # One-off maintenance scripts
├── docs/                    # VISION, STORAGE, CONTRIBUTING, ROADMAP, ...
├── REMOVED.md               # Features cut during simplification
├── Makefile
└── README.md
```

## API

The backend exposes a REST API at `http://localhost:8000/api`:

| Endpoint | Description |
|----------|-------------|
| `GET /api/health` | Liveness check |
| `GET /api/dashboard` | Stats, recent songs / audio files / sessions |
| `GET /api/songs` | Song list (filterable by type, project, status, tag, search) |
| `GET /api/songs/{id}` | Song detail with takes, audio files, lyrics versions |
| `POST /api/songs` / `PATCH /api/songs/{id}` / `DELETE /api/songs/{id}` | Song CRUD (soft-delete) |
| `PUT /api/songs/{id}/lyrics` | Versioned lyrics update |
| `POST /api/songs/{id}/promote` | Promote an idea into an original |
| `GET /api/audio-files` / `PATCH /api/audio-files/{id}` | Library CRUD |
| `POST /api/audio-files/{id}/trim` | Trim a region into a new audio file |
| `GET /api/sessions` / `GET /api/sessions/{id}` | Practice sessions |
| `PATCH /api/sessions/takes/{id}` | Rate a take or add notes |
| `GET /api/setlists` / CRUD | Setlists |
| `GET /api/tabs` / CRUD | Guitar Pro tab attachments |
| `GET /api/triage` / `PATCH /api/triage/{id}` | Inbox of unclassified files |
| `POST /api/upload` | Drag-drop ingest into the vault |
| `GET /api/media/audio/{id}` | Range-aware audio stream |
| `GET /api/media/take/{id}/audio` | Range-aware take audio stream |
| `POST /api/sync/after-practice` / `POST /api/sync/weekly` | One-button snapshot |
| `POST /api/backup/create` / `POST /api/backup/restore/{file}` | DB backup + restore |
| `GET /api/analytics/*` | Practice frequency, rating trends, skill radar, status funnel |
| `POST /api/gopro/analyze` / `POST /api/gopro/process` | Video-to-clip pipeline |
| `GET /api/options` / CRUD | Dropdown options (sources, roles, projects, tunings) |
| `GET /api/tags` / CRUD | Tags across songs / takes / audio files |
| `GET /api/trash` / restore | Soft-deleted song cleanup |
| `POST /api/feedback` | In-app feedback (files a GitHub issue) |

## License

MIT
