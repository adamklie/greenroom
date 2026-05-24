# Data Ingestion

How music data enters Greenroom. The full operational details (ffmpeg invocations, cuts.txt format, naming conventions) live in code — this is just the map.

## Where each kind of file ends up

| Source | Format | Lands in | Ingested by |
|---|---|---|---|
| GoPro at band practice | Long .MP4 | `Ozone Destructors/Practice Sessions/{date}/` | Process page → `gopro.py` router cuts the video using a `cuts.txt`, then `bootstrap.py` scans the resulting clips into PracticeSession + AudioFile rows |
| Phone quick capture | .m4a / .mov | `Ideas/` or `Solo/` | Drag-drop into Library (Import page) → `upload.py` → vault ingest |
| Logic Pro / GarageBand export | .m4a / .wav | `Solo/` | Same — Import page |
| Sural collaborator tracks | .m4a / .mp3 | `Sural/{songname}/` | Import page; manual song-link in Library |
| Backing tracks (YouTube etc) | .mp3 / .mp4 | `Backing Tracks/` | Import page |
| Direct upload via UI | any audio/video | R2 (or local vault in dev) | `POST /api/upload` → `vault.ingest()` |

## The two ingestion entry points

**1. `make bootstrap`** — Owner-only CLI. Walks `~/Library/Mobile Documents/com~apple~CloudDocs/greenroom/` (or `GREENROOM_VAULT_DIR`), finds practice sessions, ingests anything new. Idempotent. Lives in `backend/scripts/bootstrap.py`.

**2. `POST /api/upload`** — Browser drag-drop via the Import page. Hashes the file → assigns a content-addressed identifier (`AFXXXXXXX`) → writes to vault (R2 or local) → inserts `audio_files` row. Code at `backend/app/routers/upload.py`; vault storage abstracted via `backend/app/services/vault.py`.

## File types accepted

| Extension | Audio/Video | Notes |
|---|---|---|
| `.m4a`, `.mp3` | Audio | Primary playback formats |
| `.wav` | Audio | Raw stems — sometimes flagged separately |
| `.mp4`, `.mov` | Video | Played in browser via `<video>`; can be processed by Process page |
| `.MP4` | Video (GoPro) | Source for Process; not directly playable |
| `.band` | GarageBand | Must be exported to m4a first; not auto-ingestable |
| `.gp`–`.gp7`, `.gpx` | Guitar Pro tabs | Uploaded via the Tabs page, not vault |

## When something doesn't appear in the Library

Two common reasons:
- File is in the vault but no `audio_files` row exists yet → re-run `make bootstrap` locally, or upload via Import page
- File is on disk in a location bootstrap doesn't scan (e.g. nested under `Solo/somedir/`) → move it to a top-level project folder

The Process page is for cutting one long video into multiple per-song clips; the Import page is for adding individual recordings that don't need splitting.
