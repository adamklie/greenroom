# AudioFile Unification Plan

## Goal
Treat every practice-session clip as a first-class `AudioFile`. Sessions become groupings of audio files (like setlists group songs), and the Library tab lists all audio sortable by `recorded_at`.

## Current state
- `AudioFile` (models/audio_file.py) already has `session_id`, `clip_name`, `source_video`, `start_time`, `end_time`, `video_path`, `recorded_at`, and full ratings — explicitly designed as the unified table.
- `Take` (models/take.py) is the legacy parallel table. `gopro_processor.process_session` still writes `Take` rows, so Process output never lands in the Library.
- `migrate_takes.py` service exists — partial backfill already drafted.
- 7 routers + several services still reference `Take` directly.

## Target model
- **AudioFile** = unit of audio. A practice clip is an AudioFile with `session_id` + `recorded_at` set. Solo recordings, Sural collabs, Suno, etc. are AudioFiles without `session_id`.
- **PracticeSession** = metadata (date, project, folder, notes). Its audio is `AudioFile.filter(session_id=...)`.
- **Library tab** = all AudioFiles, sortable by `recorded_at`, filterable by session/project/role.
- **Sessions tab** = sessions listed by date; expanding a session shows its AudioFiles inline.

## Phases

### Phase 1 — Backfill (c)
1. Review + finish `migrate_takes.py`. Verify it copies: file_path (from audio_path), session_id, song_id, clip_name, source_video, start/end_time, video_path, ratings (int→float, 1-5→0.5-5 scale check), notes, created_at.
2. Set `recorded_at = session.date` for each migrated row.
3. Set `role = "practice_clip"`, `source = project` (e.g. "ozone_destructors").
4. Back up DB first (`backups/` dir exists). Run migration. Spot-check a few sessions.
5. Do NOT drop Take table yet — keep until readers are ported.

### Phase 2 — Process writes AudioFile (b)
1. `gopro_processor.process_session` creates AudioFile rows (not Take). Sets session_id, recorded_at, role, source, clip_name, source_video, start/end_time, video_path, file_path.
2. Reprocess the 9 files from GX010033/GX020033 against the correct date (2026-3-22) to validate — then delete the orphan 2026-4-12 outputs.
3. Rename existing disk files from 2026-4-12 → 2026-3-22 OR reprocess from source on Desktop. Decide which.

### Phase 3 — Port readers
1. Update routers one at a time: sessions.py, media.py, repertoire.py, songs.py, analytics.py, dashboard.py, sync.py, dedup.py. Each switches from `Take` queries to `AudioFile.filter(session_id is not None)` or equivalent.
2. Update frontend Sessions tab to hit the new shape.
3. Add Library tab sort-by-recorded_at + session filter.

### Phase 4 — Retire Take
1. Drop `take_tags` junction (move tags to `audio_file_tags` — the TODO in audio_file.py).
2. Drop `takes` table.
3. Remove `models/take.py`, `migrate_takes.py`, references in `models/__init__.py` and `models/session.py`.

## Decisions
- **Ratings**: cast int→float directly. User will re-rate if anything looks off.
- **Tags**: build `audio_file_tags` junction up front (not deferred to Phase 4) and migrate `take_tags` rows during backfill, so new AudioFiles can be tagged immediately.
- **Rename `source_video` → `source_file`** on AudioFile. User may want to cut audio-only sources in the future, not just video.
- **No `Take` alias** — hard-cut each router during Phase 3. Take has no conceptual role separate from AudioFile.
- **2026-4-12 → 2026-3-22 cleanup**: rename in place (disk + DB). Don't reprocess from Desktop GX sources unless rename fails.

## Immediate next action
Phase 1: read `migrate_takes.py` end-to-end, patch gaps (especially `recorded_at`, `role`, `source`), back up DB, run it.
