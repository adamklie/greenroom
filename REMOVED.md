# Removed features — MVP 1.0 simplification

Greenroom v2 reframed the app as a song record-keeping tool. Anything not in service of "edit a song row, attach a recording, rate it, find it later" was cut on the `feat/simplify-v2` branch.

To bring a feature back, revert the listed commit SHAs (in reverse order) or check them out as a starting point.

| Feature | Files removed | DB tables affected | Why removed | Bring-back complexity | Commit SHA(s) |
|---|---|---|---|---|---|
| Content Planner | `backend/app/routers/content.py`, `backend/app/schemas/content.py`, `backend/app/models/content.py`, `frontend/src/pages/ContentPlanner.tsx`, `api.content.*` in client.ts, `ContentPost` references in `backend/app/services/backup.py` | `content_posts` (drop via `scripts/drop_simplified_tables.py`) | Social-media kanban is out of scope for "song record-keeping" | Low | 48e156c (frontend), 53d7723 (backup decoupling), 5b09d6f (backend) |
| Discover / Apple Music | `backend/app/routers/apple_music.py`, `backend/app/services/apple_music.py`, `backend/app/models/listening.py`, `backend/scripts/ingest_apple_dump.py`, `backend/scripts/link_listening_to_songs.py`, `frontend/src/pages/Discover.tsx`, `api.appleMusic.*` in client.ts, `apple_play_count` + `apple_last_played` fields on `SongRead` + `_songs_to_read_bulk` aggregation in `backend/app/routers/songs.py` | `listening_history`, `listening_plays`, `apple_playlists`, `apple_playlist_tracks` (drop via `scripts/drop_simplified_tables.py`) | Listening-history surfacing isn't record-keeping; cuts a large slice of incidental complexity | Medium (the ingest pipeline is non-trivial to recreate) | 48e156c (frontend), 39f04fa (songs decoupling), 5b09d6f (backend) |
| Recommendations | `backend/app/routers/recommendations.py`, `backend/app/services/recommendations.py`, `RecommendationsCard` in `frontend/src/pages/Dashboard.tsx`, `api.recommendations.*` in client.ts | none (pure derivation over Song/Take/Session) | Career-manager feature — implicitly tells the user what to do, which is not the goal | Low | 0850ecf (frontend), 5b09d6f (backend) |
| Dedup admin | `backend/app/routers/dedup.py`, `DedupSection` in `frontend/src/pages/Settings.tsx`, `api.dedup.*` in client.ts | none | One-time cleanup task; lives better as a maintenance script if dupes show up again | Low | f257579 (frontend), 5b09d6f (backend) |
| Reorganize admin | `backend/app/routers/reorganize.py`, `backend/app/services/reorganize.py`, `api.reorganize.*` in client.ts | none | Redundant with `app/services/autosync.py`, which already moves files on song update. (The UI side was already gone from `Sync.tsx` pre-v2.) | Low | 5b09d6f |
| Roadmap (dead code) | `backend/app/models/roadmap.py`, `backend/app/schemas/roadmap.py`, `parse_roadmap` + `ParsedRoadmapTask` in `backend/app/services/markdown_parser.py` | `roadmap_tasks` (drop via `scripts/drop_simplified_tables.py` if it exists) | Pure dead code — never registered as a router, never referenced from another module | Low | 5b09d6f |
| Repertoire (dead code) | `backend/app/routers/repertoire.py` | none | Pure dead code — never registered in `main.py`. Looks like an earlier draft of `songs.py` | Low | 5b09d6f |

## What was kept

These were *not* cut, despite appearing on earlier prune lists:

- **Feedback** — User actively fixed this on `main` (commit afce25c on origin/main) and finds it useful for filing issues without leaving the app.
- **Process / GoPro** — Reframed as a general video-to-clip cutter, not a band-practice-specific tool. Still useful for any long video that needs splitting into per-song clips.
- **Filebrowser** — Required by the Process modal.

## Cleanup

After merging `feat/simplify-v2`:

```bash
python scripts/drop_simplified_tables.py
```

Drops the orphaned tables. Idempotent — safe to re-run.
