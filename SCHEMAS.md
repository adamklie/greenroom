# Greenroom Data Schemas

Last updated: 2026-04-09

## Object Hierarchy

```
AudioFile (the atom — a single recording on disk)
    ↓ belongs to (optional)
Song (a musical work — groups related audio files)
    ↓ belongs to (optional)
Setlist (an ordered list of songs for a performance)
Album (a curated collection of songs for release)
```

---

## AudioFile

The fundamental unit. A single audio or video recording that exists on disk.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | auto | Primary key |
| file_path | string | yes | Path relative to music_dir (or absolute) |
| file_type | string | no | Extension: m4a, mp3, wav, mp4, mov |
| song_id | int (FK) | no | Which song this belongs to. Null = unassigned |
| source | string | no | Where it came from: phone, logic_pro, garageband, suno_ai, gopro, collaborator, download, unknown |
| role | string | no | What role it plays: recording, demo, reference, backing_track, final_mix, stem |
| version | string | no | Version label: v1, v2, FINAL, etc. |
| is_stem | bool | no | True if this is an individual instrument track, not a mix |
| rating_overall | int (1-5) | no | Overall quality rating |
| rating_vocals | int (1-5) | no | Vocal performance rating |
| rating_guitar | int (1-5) | no | Guitar performance rating |
| rating_drums | int (1-5) | no | Drum performance rating |
| rating_tone | int (1-5) | no | Sound/tone quality rating |
| rating_timing | int (1-5) | no | Timing/rhythm rating |
| rating_energy | int (1-5) | no | Energy/feel rating |
| notes | text | no | Free-text notes about this specific recording |
| created_at | datetime | auto | When the record was created |

**Behaviors:**
- When `song_id` changes, file auto-moves to the song's organized folder
- When `song_id` is null, file lives in `_inbox/`
- Soft-deletable: moves to `_trash/`, purged after 30 days
- Content-hashable for auto-heal if moved externally

---

## Song

A musical work. Groups related audio files together. All fields except `title` are optional.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | auto | Primary key |
| title | string | yes | Song name |
| artist | string | no | Original artist (for covers) |
| type | string | no | cover, original, idea — determines which filtered view it appears in |
| status | string | no | Progress: idea, learning, rehearsed, polished, recorded, released (varies by type) |
| project | string | no | Context: solo, ozone_destructors, sural, joe |
| key | string | no | Musical key: C, Am, F#m, Bb, etc. |
| tempo_bpm | int | no | Beats per minute |
| tuning | string | no | Guitar tuning: standard, drop_d, open_g, half_step_down, etc. |
| vibe | string | no | Free-text mood/feel: "upbeat", "melancholy folk", etc. |
| lyrics | text | no | Current version of lyrics |
| notes | text | no | Free-text notes about the song/composition |
| reference_audio_file_id | int (FK) | no | The original artist's recording (for covers) |
| promoted_from_id | int (FK) | no | If this was promoted from an idea, links back to it |
| rating_overall | int (1-5) | no | Song-level overall rating |
| rating_vocals | int (1-5) | no | How good are the vocals on this song generally |
| rating_guitar | int (1-5) | no | Guitar parts quality |
| rating_drums | int (1-5) | no | Drum parts quality |
| rating_tone | int (1-5) | no | Sound quality |
| rating_timing | int (1-5) | no | Timing quality |
| rating_energy | int (1-5) | no | Energy/feel |
| times_practiced | int | no | How many sessions include this song |
| created_at | datetime | auto | |
| updated_at | datetime | auto | |

**Relationships:**
- Has many AudioFiles (via audio_files.song_id)
- Has many Takes (via takes.song_id)
- Has many Tags (M2M via song_tags)
- Has many LyricsVersions (auto-versioned when lyrics change)

**Behaviors:**
- When type, project, title, or artist changes → all audio files auto-move to match
- Deleting a song soft-deletes: files move to `_trash/`, song marked status="deleted"
- Ideas can be promoted to originals (creates new song, links via promoted_from_id)

---

## Take

A clip from a practice session. Essentially an AudioFile with session context (timestamps, source video).

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | auto | Primary key |
| session_id | int (FK) | yes | Which practice session |
| song_id | int (FK) | no | Which song this is a take of |
| clip_name | string | yes | Name of the clip: "your_touch", "creep_2" |
| source_video | string | no | Original GoPro file: "GX010033.MP4" |
| start_time | string | no | Start timestamp in source video: "00:06:30" |
| end_time | string | no | End timestamp: "00:11:00" |
| video_path | string | no | Path to extracted video clip |
| audio_path | string | no | Path to extracted audio |
| rating_overall | int (1-5) | no | Same 7-dimension rating system |
| rating_vocals | int (1-5) | no | |
| rating_guitar | int (1-5) | no | |
| rating_drums | int (1-5) | no | |
| rating_tone | int (1-5) | no | |
| rating_timing | int (1-5) | no | |
| rating_energy | int (1-5) | no | |
| notes | text | no | Notes about this specific take |
| created_at | datetime | auto | |

**Relationships:**
- Belongs to PracticeSession
- Belongs to Song (optional)
- Has many Tags (M2M via take_tags)

---

## PracticeSession

A dated practice event containing multiple takes.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | auto | Primary key |
| date | date | yes | Session date |
| project | string | yes | Which band/context |
| folder_path | string | yes | Relative path to session folder (unique) |
| notes | text | no | Session-level notes |
| created_at | datetime | auto | |

**Relationships:**
- Has many Takes

---

## Setlist

An ordered list of songs for a live performance.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | auto | Primary key |
| name | string | yes | Setlist name: "Open Mic Set", "OD Friday Gig" |
| description | text | no | Context, venue info, etc. |
| config | string | no | Performance config: solo, duo, full_band |
| created_at | datetime | auto | |
| updated_at | datetime | auto | |

**Relationships:**
- Has many SetlistItems (ordered)

## SetlistItem

A song in a setlist at a specific position.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | auto | Primary key |
| setlist_id | int (FK) | yes | Which setlist |
| song_id | int (FK) | yes | Which song |
| position | int | yes | Order in the setlist (0-indexed) |
| duration_minutes | int | no | Estimated duration (default 4) |
| notes | text | no | Performance notes: "start with acoustic intro" |

---

## Album (Future)

A curated collection of songs for release/distribution.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | auto | Primary key |
| name | string | yes | Album/EP name |
| description | text | no | |
| release_date | date | no | Target or actual release date |
| artwork_path | string | no | Cover art file path |
| created_at | datetime | auto | |

**Relationships:**
- Has many AlbumTracks (ordered, with specific AudioFile per track)

---

## Tag

A label that can be applied to Songs or Takes.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | auto | Primary key |
| name | string | yes | Tag name (unique): "needs-work", "crowd-pleaser" |
| category | string | no | Grouping: take, song, general |
| color | string | no | Hex color for UI rendering |
| is_predefined | bool | no | True = system tag, False = user-created |

**Predefined tags:**
- Take: needs-work, good-take, false-start, best-take
- Song: live-ready, needs-lyrics, needs-arrangement, crowd-pleaser, setlist-candidate
- General: demo, final-mix, archived

---

## LyricsVersion

Version history for song lyrics. Auto-created when lyrics are updated.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | auto | Primary key |
| song_id | int (FK) | yes | Which song |
| version_number | int | yes | Sequential version (1, 2, 3...) |
| lyrics_text | text | yes | The lyrics at this version |
| change_note | string | no | What changed: "added bridge", "rewrote chorus" |
| created_at | datetime | auto | |

---

## ListeningHistory

Imported from Apple Music. Read-only reference data.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | auto | Primary key |
| title | string | yes | Track name |
| artist | string | yes | Artist name |
| play_count | int | no | Times played in Apple Music |
| genre | string | no | Genre tag |
| duration_seconds | int | no | Track length |
| is_own_recording | bool | no | True if artist matches user |
| linked_song_id | int | no | If matched to a Song in the catalog |

---

## TriageItem

Files discovered on disk that couldn't be auto-classified.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | auto | Primary key |
| file_path | string | yes | Where the file was found |
| file_type | string | no | Extension |
| suggested_song_id | int | no | Best-guess song match |
| suggested_type | string | no | Best-guess type |
| suggested_source | string | no | Best-guess source |
| status | string | yes | pending, classified, skipped |
| discovered_at | datetime | auto | |

---

## ContentPost

Planned social media content.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| id | int | auto | Primary key |
| title | string | yes | Post title/description |
| song_id | int (FK) | no | Linked song |
| take_id | int (FK) | no | Linked take |
| audio_file_id | int (FK) | no | Linked audio file |
| platform | string | no | instagram, tiktok, youtube |
| post_type | string | no | reel, story, post, video |
| scheduled_date | date | no | When to post |
| status | string | no | planned, ready, posted |
| caption | text | no | Post caption |
| notes | text | no | Internal notes |
| created_at | datetime | auto | |
| updated_at | datetime | auto | |
