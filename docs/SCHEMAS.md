# Greenroom Data Schemas

Last updated: 2026-05-24

Table-by-table reference for the SQLAlchemy models in `backend/app/models/`.
This doc tracks the live schema — if you change a model, update the matching
section here.

## Object Hierarchy

```
AudioFile (the atom — a single recording on disk, audio or video)
    ↓ belongs to (optional)
Song (a musical work — groups related audio files)
    ↓ referenced by
Setlist + SetlistItem (an ordered list of songs for a performance)

PracticeSession (a dated practice event)
    ↑ referenced by
AudioFile.session_id  (clips from that session)
```

`AudioFile` is canonical. Practice clips are AudioFiles with `session_id` and
`recorded_at` set; solo recordings, Suno output, collabs are AudioFiles with
those fields null. The legacy `Take` table is deprecated (see below).

---

## AudioFile (`audio_files`)

The fundamental unit. All audio + video lives here: solo recordings, practice
clips, collabs, AI output, references — everything.

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| song_id | int FK → songs | Null = unassigned |
| file_path | str unique | Vault filename, e.g. `AF12AB34CD.mp3` |
| file_type | str? | Extension: m4a, mp3, wav, mp4, mov |
| identifier | str unique? | `AF` + 8-hex (sha256 of name+ts) |
| submitted_file_name | str? | Original filename at upload time |
| source | str? | phone, logic_pro, gopro, suno_ai, collaborator, ... |
| role | str? | recording, demo, reference, practice_clip, ... (default `recording`) |
| version | str? | v1, v2, FINAL, ... |
| is_stem | bool | True if individual instrument track, not a mix |
| session_id | int FK → practice_sessions? | Set when this clip came from a practice session |
| clip_name | str? | Clip label, e.g. `your_touch`, `creep_2` |
| source_file | str? | Original source video (e.g. `GX010033.MP4`) — renamed from `source_video` |
| start_time / end_time | str? | Timestamps in source file: `00:06:30` |
| video_path | str? | Path to extracted video clip (if applicable) |
| rating_overall / vocals / guitar / drums / tone / timing / energy / keys / bass / mix / other | float? | 11 dimensions, 0.5–5.0 in half-star increments |
| notes | text? | Free-text |
| created_at | datetime | Row creation |
| uploaded_at | datetime? | When imported into Greenroom |
| recorded_at | datetime? | When the audio was actually recorded |

**Relationships:** belongs to `Song` (optional), belongs to `PracticeSession`
(optional), has many `Tag` via `audio_file_tags`.

---

## Song (`songs`)

A musical work. Groups related audio files together.

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| title | str | Required |
| artist | str? | Original artist (for covers) |
| type | str? | `cover`, `original`, `idea` |
| status | str? | Progress along the type's flow (see below) |
| project | str? | `solo`, `ozone_destructors`, `sural`, `joe` |
| key | str? | Musical key: C, Am, F#m, Bb, ... |
| tempo_bpm | int? | |
| tuning | str? | `standard`, `drop_d`, `open_g`, ... (default `standard`) |
| vibe | str? | Free-text mood/feel |
| lyrics | text? | Current version (history in `lyrics_versions`) |
| reference_audio_file_id | int FK → audio_files? | Reference recording for covers |
| promoted_from_id | int FK → songs? | If promoted from an idea, links back |
| rating_overall / vocals / guitar / drums / tone / timing / energy | int? | Song-level (integer 1–5) |
| is_original | bool | Legacy flag, default False |
| times_practiced | int | Default 0 |
| notes | text? | |
| created_at, updated_at | datetime | |

**Status flows:**

```
Cover:    idea → learning → rehearsed → polished → recorded → released
Original: idea → draft → arranged → rehearsed → recorded → released
Idea:     captured → developing → promoted   (graduates to original)
```

**Relationships:** has many `AudioFile`, `LyricsVersion`, `Tag` (via
`song_tags`); reciprocal `Take` relationship still wired for legacy reasons
(see deprecation note below).

---

## PracticeSession (`practice_sessions`)

A dated practice event. Audio is reached via `AudioFile.session_id`.

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| date | date | Session date (required) |
| project | str | Required (`solo`, `ozone_destructors`, ...) |
| folder_path | str unique | Path to session folder (legacy from pre-unification) |
| notes | text? | |
| created_at | datetime | |

---

## Setlist + SetlistItem (`setlists`, `setlist_items`)

An ordered list of songs for a performance.

**Setlist:**

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| name | str | Required |
| description | text? | |
| config | str | `solo`, `duo`, `full_band` (default `full_band`) |
| created_at, updated_at | datetime | |

**SetlistItem:**

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| setlist_id | int FK → setlists | |
| song_id | int FK → songs | |
| position | int | 0-indexed order |
| duration_minutes | int | Estimated, default 4 |
| notes | text? | "start with acoustic intro", etc. |

Items are loaded ordered by `position` with `cascade="all, delete-orphan"`.

---

## User + MagicToken (`users`, `magic_tokens`)

Added in the auth phase (post-cloud-deploy). Admin-invite-only — no signup
flow. See [ARCHITECTURE.md § 6](ARCHITECTURE.md#6-auth-model) for the magic-
link flow.

**User:**

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| email | str unique | Required |
| role | str | `viewer`, `editor`, or `admin`. Enforced in `auth/deps.py`, not as a DB CHECK constraint |
| invited_by_id | int FK → users? | Self-ref |
| created_at | datetime | |
| last_login_at | datetime? | |

**MagicToken:**

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| user_id | int FK → users | |
| token_hash | str unique | sha256 of the raw urlsafe token — raw is never stored |
| expires_at | datetime | 15 min after issue |
| used_at | datetime? | Single-use — set on exchange |
| created_at | datetime | |

JWT session cookies (`greenroom_session`) are HS256-signed with
`GREENROOM_AUTH_SECRET`, 7-day expiry, `HttpOnly; SameSite=Lax; Secure`.

---

## Tag (`tags`) + junctions

Many-to-many label applied to Songs, Takes, and AudioFiles.

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| name | str unique | |
| category | str | `take`, `song`, `general` (default `general`) |
| color | str? | Hex |
| is_predefined | bool | Default True; user-created tags set False |

Junction tables (all `ondelete="CASCADE"`):

- `song_tags(song_id, tag_id)`
- `take_tags(take_id, tag_id)` — legacy, will retire with Take
- `audio_file_tags(audio_file_id, tag_id)`

Predefined tags seeded on first boot (see `PREDEFINED_TAGS` in
`models/tag.py`): `needs-work`, `good-take`, `false-start`, `best-take`,
`demo`, `final-mix`, `live-ready`, `needs-lyrics`, `needs-arrangement`,
`crowd-pleaser`, `setlist-candidate`, `archived`.

---

## LyricsVersion (`lyrics_versions`)

Auto-created when a song's lyrics are updated.

| Field | Type | Notes |
|---|---|---|
| id | int PK | |
| song_id | int FK → songs (CASCADE) | |
| version_number | int | Sequential 1, 2, 3, ... |
| lyrics_text | text | The lyrics at this version |
| change_note | str? | "added bridge", "rewrote chorus" |
| created_at | datetime | |

---

## Annotation summary

**Ratings:** 11 dimensions on `AudioFile` (float, 0.5–5.0 in half-star
increments), 7 dimensions on `Song` (int, 1–5).
Dimensions: Overall, Vocals, Guitar, Drums, Tone, Timing, Energy
(+ Keys, Bass, Mix, Other for AudioFile).

**Tags:** category-scoped, applied to Songs / AudioFiles (and legacy Takes).
Predefined list above; users can add custom strings.

**Structured fields (Song):** Key, Tempo (BPM), Tuning, Vibe.

---

## Deprecated

### Take (`takes`)

The Take table is **deprecated** and no longer read or written by the app —
practice clips are `AudioFile` rows with `session_id` set; Library + Sessions
read from `AudioFile` only. The `takes` table and `models/take.py` still
exist for now because a handful of legacy callers reference them; both will
be dropped together when the legacy callers are removed. Until then the table
is vestigial and harmless.

Don't add new code that reads or writes `Take`. Use `AudioFile`.
