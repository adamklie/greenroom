# Greenroom

A music career manager for aspiring musicians. Track your repertoire, rate practice takes, plan social media content, and follow a roadmap from bedroom to stage.

## Features

- **Dashboard** — Career stats, roadmap progress with checklists, songs by status
- **Repertoire Manager** — Searchable song catalog with status tracking (idea → rehearsed → polished → recorded → released), inline audio playback
- **Practice Session Browser** — Browse sessions by date, listen to takes in-browser, rate with 1-5 stars
- **Content Planner** — Kanban board for social media posts (Planned → Ready → Posted) linked to songs and recordings

## Tech Stack

- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Media:** Native HTML5 audio/video streaming via FastAPI

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+

### Recommended layout

- Repo (code + live DB): `~/greenroom` — **not in iCloud**, backed up via GitHub
- Vault (music files, DB backups, annotation exports): `~/Library/Mobile Documents/com~apple~CloudDocs/greenroom/` — auto-created on first run, iCloud-synced

See [docs/STORAGE.md](docs/STORAGE.md) for the full picture.

### Setup

```bash
# Clone to ~/greenroom (outside iCloud)
git clone https://github.com/adamklie/greenroom ~/greenroom
cd ~/greenroom

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

By default, Greenroom looks for a music directory one level up from the project root. Override with:

```bash
export GREENROOM_MUSIC_DIR=/path/to/your/music
```

## How It Works

Greenroom reads your existing music directory structure:

```
music/
├── Solo/                    # Solo recordings
├── Sural/                   # Collaboration projects
├── Ozone Destructors/       # Band practice sessions
│   └── Practice Sessions/
│       └── YYYY-M-D/
│           ├── cuts.txt     # Timestamps: START END clip_name
│           └── cuts/        # Extracted video clips
├── Ideas/                   # Rough demos
├── _audio_exports/          # Extracted audio from video clips
├── REPERTOIRE.md            # Song catalog (parsed into database)
├── ROADMAP.md               # Career roadmap (parsed into database)
└── greenroom/               # This app
```

Run `make bootstrap` to scan the filesystem and populate the SQLite database. The bootstrap is idempotent — re-run it anytime you add new sessions or recordings.

## Project Structure

```
greenroom/
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app
│   │   ├── config.py        # Settings (music dir, DB path)
│   │   ├── database.py      # SQLAlchemy setup
│   │   ├── models/          # ORM models (Song, Session, Take, etc.)
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── routers/         # API route handlers
│   │   └── services/        # Bootstrap, parsers, scanners
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Shell with sidebar navigation
│   │   ├── api/client.ts    # Typed API client
│   │   └── pages/           # Dashboard, Repertoire, Sessions, ContentPlanner
│   └── package.json
├── Makefile
└── README.md
```

## API

The backend exposes a REST API at `http://localhost:8000/api`:

| Endpoint | Description |
|----------|-------------|
| `GET /api/dashboard` | Stats, roadmap phases, recent activity |
| `GET /api/repertoire` | Song list (filterable by project, status, search) |
| `GET /api/repertoire/{id}` | Song detail with takes and audio files |
| `PATCH /api/repertoire/{id}` | Update song status or notes |
| `GET /api/sessions` | Practice session list |
| `GET /api/sessions/{id}` | Session detail with takes |
| `PATCH /api/sessions/takes/{id}` | Rate a take or add notes |
| `GET /api/media/take/{id}/audio` | Stream take audio |
| `GET /api/media/audio/{id}` | Stream audio file |
| `GET /api/content/posts` | Content plan list |
| `POST /api/content/posts` | Create a planned post |
| `POST /api/bootstrap/scan` | Re-scan filesystem |

## License

MIT
