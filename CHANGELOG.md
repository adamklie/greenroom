# Changelog

All notable changes to Greenroom are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Import tab can **group an upload into a session**: a "Group these files into a
  session" toggle reveals a session **name** + **date**, creates one session, and
  attaches every uploaded file to it (`POST /api/sessions`; `/api/upload` accepts
  `session_id`). Plus an **"Upload folder"** button (whole-folder selection).
- Sessions now have an optional **name** (UI shows it as the title, falling back
  to the date). Adds a nullable `name` column.

### Changed
- Imported **video files keep their video** (the clip plays as video; audio
  extracts on demand) instead of being stripped to m4a on upload.
- Renamed the DB table `practice_sessions` → `sessions` to match what the API
  and UI already call them (migration `d4e5f6a7b8c9`; child FK references
  repointed). The Python model class stays `PracticeSession` to avoid colliding
  with SQLAlchemy's `Session`.

## [2.0.0] - 2026-06-14

**Multi-project is live.** Greenroom is now multi-tenant: the
`GREENROOM_MULTI_PROJECT` flag is enabled in production, so every user signs in
to a sidebar **project switcher** and sees only the projects they belong to.
Per-project **owner / editor / viewer** roles; **invite-only** sharing by email;
one active project at a time. Read/write isolation is enforced centrally and
fails closed. No data migration was needed at flip time — production data was
already backfilled with `project_id` (Phase 3a) and is unchanged.

### Added
- Drag-and-drop **project reordering** in Settings → Project settings (a
  `position` column, migration `c3d4e5f6a7b8`; `POST /api/projects/reorder`),
  driving the sidebar switcher order.
- Recording-level **move/split**: moving a single recording to another project
  splits it into the destination's matching song — creating that song there if
  needed (optional copy-metadata), via a searchable song picker. Mixed-song bulk
  moves warn before auto-matching by title+artist. Available anywhere a track is
  shown (Library, Songs, Sessions).
- v2 project settings — a **Settings → Project settings** section with a project
  picker, editable **name** + **description**, a **color** (shown as a dot in the
  sidebar switcher), inline **member management**, and **delete** (empty projects
  only). Adds `description`/`color` columns to `projects` (migration
  `b2c3d4e5f6a7`); `PATCH`/`DELETE /api/projects/{id}` and
  `GET /api/projects/{id}/songs`.
- v2 multi-project groundwork (Phase 3a) — behind the default-off
  `GREENROOM_MULTI_PROJECT` flag, so **no behavior change yet**: `projects` and
  `project_members` tables, a nullable `project_id` on songs / sessions / audio
  files / takes / setlists (migration `f1a2b3c4d5e6`), and
  `scripts/backfill_projects.py` to populate it from the legacy `project`
  string. Additive and reversible (clean downgrade; legacy `project` retained).
- v2 multi-project enforcement (Phase 3b) — also behind the default-off flag,
  **inert until it flips**: per-request project scoping via the
  `X-Greenroom-Project` header, a `require_project_role` gate, automatic
  `project_id` stamping on new rows, cross-project write validation, and a
  `/api/projects` CRUD + membership API. Read isolation is enforced centrally by
  a `do_orm_execute` query filter (fails closed; covers relationship loads).
  HTTP- and ORM-level isolation test suites added.
- v2 multi-project frontend (Phase 3b) — a sidebar **project switcher** and basic
  **members/sharing** panel, driven by `/api/projects`; the API client sends the
  active project as `X-Greenroom-Project` on every request. All gated on the
  `multi_project` flag now reported by `/api/health`, so the UI is unchanged
  (no switcher, legacy project pickers intact) while the flag is off.
- v2 project scoping for native browser requests — the active project is mirrored
  into a `greenroom_project` cookie, which the auth gate reads as a fallback to
  the header. This scopes `<audio>`/download/tab requests (which can't send a
  custom header) once the flag is on; membership is still verified, so the cookie
  only narrows scope. Unblocks the eventual flag flip.
- v2 admins are now **scoped to the active project** on data routes (when one is
  selected) instead of always seeing everything merged — so the project switcher
  filters an admin's view like any member's. Admins still reach any project
  without a membership row, and the cross-project ops tools (admin-only) are
  unaffected. With no project selected, admins remain unscoped.
- Move items between projects (v2) — reassign songs, sessions, audio files,
  takes, and setlists to another project via `POST /api/projects/move` and a
  "Move to…" menu in the song detail panel, the Library bulk toolbar, and the
  Sessions/Setlists cards. Moving a song or session cascades `project_id` to its
  recordings/takes so media never gets split from its song. The request is
  scoped to the source project (you can't move items you can't see) and the
  target requires owner/editor (or admin) rights.

### Changed
- Brand refresh: custom Greenroom waveform-G icon set for the nine content nav
  tabs, a logo lockup in the sidebar, a matching favicon, and a wordmark +
  stack badges in the README header (assets in `frontend/src/components/
  GreenroomIcons.tsx`, `frontend/public/favicon.svg`, `greenroom-wordmark.svg`).
- The ops/maintenance endpoints (integrity, file health/move/consolidate, file
  browser, raw file streaming, cross-project dedup, and DB backup/restore/export)
  are now **admin-only**, up from editor/viewer. With the multi-project flag off
  this only affects non-admin users of those maintenance tools; data routes are
  unchanged.
- Dashboard reorganized — all totals (songs, sessions, covers, originals, ideas)
  surfaced at the top using the new icon set; "Songs by Project" removed; Focus
  Songs retained.
- Navigation/UX cleanup — removed the in-app **Process** tab (the GoPro clipper
  is a standalone tool now), moved **Feedback** to the bottom of the nav, renamed
  "Practice Sessions" → **Sessions**, and dropped the Sessions "Best Tracks" tab
  and the Setlists empty-state subtitle.
- Browser-tab favicon now ships **raster fallbacks** (PNG + a multi-size
  `favicon.ico` + an apple-touch-icon) of the Greenroom G, so the logo shows in
  browsers that don't render SVG favicons (which previously fell back to the SPA
  HTML and showed a generic icon).

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
