# Changelog

All notable changes to Greenroom are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [1.2.1] - 2026-06-13

### Fixed
- `/api/health` and the OpenAPI schema now report the real package version
  (read from installed package metadata) instead of a hardcoded `0.2.0`, so
  Settings → App Info shows the correct backend version.

## [1.2.0] - 2026-06-13

Terminology: "takes" → "tracks" across the UI and the live API.

### Changed
- Renamed the user-facing "Takes" terminology to "Tracks" throughout the UI
  (songs table count column, dashboard, the Sessions "Best Tracks" tab, the
  trash/dedup view).
- Renamed the API response field `take_count` → `track_count` on songs and
  sessions (plus the frontend types and usages). It counts recordings
  (`AudioFile`s); behavior is unchanged.

### Fixed
- GoPro raw upload (`/api/gopro/upload-raw`): bind the tempfile path before
  copying so a mid-copy failure (e.g. a full disk on a multi-GB upload) can no
  longer leak the partial temp file.

### Note
- The deprecated `Take` table still backs the Sessions "Best Tracks" feature,
  the dedup counts, and `analytics.py` (whose only UI consumer, the Progress
  tab, was removed in 1.1.0). Retiring `Take` and repointing those reads to
  `AudioFile` is a separate follow-up, not part of this rename.

## [1.1.0] - 2026-06-13

UI cleanup and polish pass. No data model or API contract changes.

### Added
- Import button on the Dashboard.
- The Library's searchable song picker is now reused when linking songs in the
  Import and Process tabs (one shared `InlineSongPicker` / `SongSelect`
  component), so song selection is consistent and searchable everywhere.
- Light-mode toggle in Settings is now functional and shares a single theme
  state with the sidebar toggle.
- `scripts/backfill_metadata.py` gained a `--submitted` pass that fills
  `submitted_file_name` (a readable display name) from `clip_name`, falling
  back to the file basename.

### Changed
- Sidebar nav reordered: Import now sits directly under Dashboard; Setlists
  now sits directly under Ideas.
- Trash tab renamed to "Trash & Cleanup".
- Song detail "Recordings" table: Source/Role columns widened so their
  dropdown values no longer clip, and the File column now shows the readable
  `submitted_file_name` when present instead of the raw `AF…` identifier.
- Schemas tab is now admin-only.

### Removed
- Progress tab.
- "Unrated Takes" and "Songs by Status" cards from the Dashboard.
- "Recording Integrity" card from Settings.

## [1.0.0] - 2026-06-13

Baseline release: the stable single-tenant Greenroom — Library, Songs
(covers / originals / ideas), Sessions, Setlists, Import/Process, magic-link
auth, Cloudflare R2 media storage, and continuous Litestream database
replication. Tagged as the reference point before the multi-project (v2) work.
