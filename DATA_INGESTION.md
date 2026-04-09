# Data Ingestion Guide

Last updated: 2026-04-08

## How Data Enters Greenroom

Every piece of music data follows one of these paths from **source → filesystem → database**. Each path must have a standardized process.

---

## Data Sources

| # | Source | What it produces | Where it lands | Frequency |
|---|--------|-----------------|----------------|-----------|
| 1 | GoPro at band practice | Long MP4 video files | `Ozone Destructors/Practice Sessions/{DATE}/` | Weekly |
| 2 | Phone quick capture | Voice memos, video clips | `Ideas/` or `Solo/` | Ad hoc |
| 3 | Logic Pro recording | Mixed audio (m4a/mp3) | `Solo/` | Ad hoc |
| 4 | GarageBand multi-track | .band project bundles | `Solo/2025_12_28_lpl_music/` | Rare |
| 5 | Sural (collaborator) | Produced tracks (m4a/mp3) | `Sural/{SONGNAME}/` | Ad hoc |
| 6 | Joe (collaborator) | Demo recordings (m4a/mp3) | `Joe/` | Inactive |
| 7 | Downloaded backing tracks | MP3/MP4 from YouTube etc. | `Backing Tracks/` | Ad hoc |
| 8 | Manual markdown edits | Song metadata, roadmap tasks | `REPERTOIRE.md`, `ROADMAP.md` | As needed |

---

## Ingestion Paths (Standardized)

### Path 1: Band Practice Session (GoPro → Clips → Audio → DB)

**Full workflow:**
```
1. Record on GoPro at practice
2. Create folder: Ozone Destructors/Practice Sessions/YYYY-M-D/
3. Move GoPro files into folder
4. Create cuts.txt:
     # GX010031.MP4 cuts
     00:00:00 00:04:30 song_name
     00:06:30 00:11:00 another_song
5. Create do_cuts.sh (or use make_cuts.sh)
6. Run: bash do_cuts.sh → creates cuts/*.mp4
7. Extract audio:
     for f in cuts/*.mp4; do
       ffmpeg -i "$f" -vn -acodec aac -b:a 192k \
         "_audio_exports/Ozone Destructors/YYYY-M-D/YYYY-M-D_$(basename ${f%.mp4}).m4a"
     done
8. Hit "Rescan Files" in Greenroom (or: make bootstrap)
```

**What the scanner does:** Reads cuts.txt → creates PracticeSession + Take records → links audio from `_audio_exports/`.

**What can go wrong:**
- No cuts.txt → entire session is invisible (see Path 1b below)
- Clip name doesn't match any song in REPERTOIRE.md → take is "unlinked"
- Audio not extracted → take exists but has no playable audio

### Path 1b: Legacy Session (No cuts.txt — clipped/ folder only)

15 early sessions (2025-06-22 through 2026-1-4) used a different structure:
```
YYYY-M-D/
├── clipped/          # Video clips (mp4 or mov)
├── original/         # Empty (GoPro files deleted)
```

**Current status: NOT INGESTED.** ~100 clips + extracted audio exist on disk but are invisible to the database.

**Fix:** Scanner should fall back to scanning `clipped/` directory when no cuts.txt exists.

### Path 2: Phone Quick Capture → Ideas/

```
1. Record on phone (Voice Memo, video, etc.)
2. Transfer to Mac (AirDrop, cable, etc.)
3. Rename with descriptive name (NOT "New Recording 10")
4. Move to Ideas/ directory
5. Hit "Rescan Files" in Greenroom
```

**Naming convention:** `{descriptive_name}.{ext}` — no date prefix needed, filesystem date is enough.

**What can go wrong:**
- File left at music/ root with phone-generated name (IMG_8380.mov, uuid=...mov)
- Not renamed → shows up as cryptic entry in database

### Path 3: Logic Pro Recording → Solo/

```
1. Record in Logic Pro via AudioBox iTwo
2. Export: File > Bounce > Project (or region)
3. Format: m4a (AAC) or wav
4. Name: YYYY_MM_DD_{Song_Name}.m4a
5. Save to Solo/ directory (top level)
6. Add song to REPERTOIRE.md if new
7. Hit "Rescan Files" in Greenroom
```

**Naming convention:** `YYYY_MM_DD_{Song_Name}.{ext}` — matches existing Solo/ files.

### Path 4: GarageBand Project → Export → Solo/

```
1. Open .band file in GarageBand
2. Share > Song to Music (or Export to Disk)
3. Save as: YYYY_MM_DD_{Song_Name}.m4a
4. Move to Solo/ directory
5. Add song to REPERTOIRE.md if new
6. Hit "Rescan Files"
```

**Current backlog:** 11 .band projects in `Solo/2025_12_28_lpl_music/` need this treatment:
- Go Easy On Me, Good Riddance, I Like Birds, I'm With You, Lost In My Mind (×2), Question, River, Sweet Pea, What I Got (×2)

### Path 5: Sural Collaboration → Sural/{SONGNAME}/

```
1. Sural sends a track (via AirDrop, Messages, Drive, etc.)
2. Create song folder if new: Sural/{SONGNAME}/
3. Save with version: {SONGNAME} v{N}.m4a
4. Add to REPERTOIRE.md under "Sural Project" if new song
5. Hit "Rescan Files"
```

**Naming convention:** `{SONGNAME} v{N}.m4a` — version number required for iteration tracking.

**Marking final:** Rename to `{SONGNAME} FINAL.m4a` or add notes in Greenroom.

### Path 6: Backing Track Download → Backing Tracks/

```
1. Download from YouTube or other source
2. Save to Backing Tracks/
3. Name should include: artist, song name
4. Hit "Rescan Files"
```

### Path 7: Manual Metadata → REPERTOIRE.md / ROADMAP.md

```
1. Edit REPERTOIRE.md to add/update songs
2. Edit ROADMAP.md to add/update career tasks
3. Hit "Rescan Files" (re-parses markdown into database)
```

**Or:** Edit directly in Greenroom UI (status changes, ratings, roadmap toggles persist to database without needing markdown edits).

**Note:** The database is the working copy. REPERTOIRE.md is the bootstrap source. If you edit a song's status in the UI, it won't be written back to REPERTOIRE.md — it lives in the database.

---

## Known Gaps (To Fix)

### Critical

| Gap | Impact | Fix |
|-----|--------|-----|
| 15 early sessions without cuts.txt are invisible | ~100 clips + audio orphaned | Scanner fallback to clipped/ directory |
| Solo/ subdirectories not scanned | grad_housing videos missed | Make Solo/ scan recursive |
| 170 WAV stems treated as songs | Pollutes audio_files table | Exclude raw stems or flag them |

### Important

| Gap | Impact | Fix |
|-----|--------|-----|
| 11 GarageBand projects unexported | 10+ recorded songs inaccessible | Manual export (can't automate) |
| 3 loose videos at music/ root | Orphaned, no project assignment | Triage: move to Ideas/ or delete |
| No "final version" marker for Sural tracks | Unclear which version is current | Add is_final flag or naming convention |
| old_number_seven timestamps missing (2026-3-8) | Song practiced but no take recorded | Fill in cuts.txt timestamps |
| Backing track MP4s not extracting audio | Video files in Backing Tracks/ | Extract audio or add video support |

---

## Validation Checklist

After any rescan, verify:

```
Expected counts (as of 2026-04-08):
  Songs:    ~108 (from REPERTOIRE.md)
  Sessions: 21 → should be 21+ after fixing early sessions
  Takes:    75 → should be 175+ after fixing early sessions
  Audio:    67 → should stay ~67 (minus stems if excluded)
  Roadmap:  50 tasks across 4 phases
```

Run `make bootstrap` and check output matches expectations. Investigate any drops.

---

## File Type Reference

| Extension | Type | Scanned? | Notes |
|-----------|------|----------|-------|
| .m4a | Audio (AAC) | Yes | Primary audio format |
| .mp3 | Audio (MPEG) | Yes | Secondary audio format |
| .wav | Audio (PCM) | Yes | Raw stems — should be excluded or flagged |
| .mp4 | Video (H.264) | Partial | Only in cuts/ dirs via session scanner |
| .mov | Video (QuickTime) | No | Phone/GoPro captures, not scanned |
| .MP4 | Video (GoPro) | No | Raw GoPro files, not directly scanned |
| .band | GarageBand project | Excluded | Requires manual export |
| .logicx | Logic Pro project | N/A | Not present on disk |
| .md | Markdown | Yes | REPERTOIRE.md, ROADMAP.md parsed |
