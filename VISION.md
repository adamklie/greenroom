# Greenroom — Product Vision

Last updated: 2026-04-08

## What Greenroom Is

A music portfolio builder for aspiring musicians. One central place to organize, annotate, and build your music — covers, originals, and ideas — with standardized, machine-readable data that helps you track progress, prepare for gigs, and share your work.

## Who It's For

Musicians who:
- Play covers and write originals
- Practice regularly (solo and with bands)
- Record on various devices (phone, GoPro, DAW, AI tools)
- Want to start or grow a social media presence
- Play open mics and local gigs
- Collaborate with other musicians
- Have music scattered across devices, apps, and folders

## The Three Pillars

### 1. Covers
Every cover links to the original recording as a reference point. You track your iterations — from first attempt through polished performance. Side-by-side comparison lets you hear how close you're getting.

### 2. Originals
Your own songs, tracked from initial idea through arrangement, rehearsal, recording, and release. Version history shows how a song evolves. Collaborative notes capture decisions ("Sural wants the bridge in A minor").

### 3. Ideas
A bank of raw material — voice memos, riff recordings, lyric fragments, melodic ideas. Nothing gets lost. Ideas can be promoted to originals when they're ready to develop.

## Core Principles

1. **Standardized and machine-readable.** Every piece of data has structure — typed fields, tags, ratings, not just free-text blobs. This makes everything queryable: "show me all covers in Am that are gig-ready."

2. **Workflow-first.** Every feature maps to how you actually practice, record, and perform. The app adapts to your process, not the other way around.

3. **Nothing gets lost.** Every recording, every idea, every lyric — captured and findable. The triage system catches files that fall through the cracks.

4. **Progress is visible.** You can see yourself improving over time through ratings, practice frequency, and version history.

---

## Feature Map

### Built (v2) ✓
- [x] Three-pillar song organization (covers/originals/ideas)
- [x] Structured music fields (key, tempo, tuning, vibe)
- [x] Multi-dimensional ratings (overall, vocals, guitar, drums, tone, timing, energy)
- [x] Tags system (predefined + custom, on songs and takes)
- [x] Lyrics editor with version history
- [x] Practice session browser with 224 takes across 21 sessions
- [x] Audio playback in-browser for all recordings
- [x] Inline editing of all song metadata (reclassify, rename, reassign)
- [x] Idea → Original promotion
- [x] Triage queue for unclassified files (129 items)
- [x] File health check (detect broken links)
- [x] File consolidation (pull scattered files into organized directory)
- [x] Setlist builder with running time
- [x] Social media content planner (kanban: planned → ready → posted)
- [x] Dashboard with portfolio stats
- [x] Dark/light mode
- [x] Filesystem bootstrap (scans ~/Desktop/music, ~/Music, ~/Desktop)
- [x] Rescan button for live filesystem updates

### Next Up — High Impact

#### GoPro Session Workflow (automates your most tedious process)
The cutting workflow today is manual: write cuts.txt, write do_cuts.sh, run ffmpeg. This should be a guided flow in the app:
- Upload or point to GoPro video files
- Playback in-browser with a timeline
- Click to mark start/end points for each song
- Name each clip, assign to a song
- One-click: cut video, extract audio, create take records
- Auto-generate cuts.txt for archival compatibility

#### Practice Progress Visualization
You have 224 takes across 21 sessions but no way to see trends:
- Rating history per song over time (are you getting better?)
- Practice frequency heatmap (how often are you playing?)
- "Most improved" and "needs attention" highlights
- Per-dimension trends (vocals improving? timing slipping?)

#### Import Workflow (drag-and-drop new recordings)
Right now new recordings enter via filesystem + rescan. Should be:
- Drag a file onto the app (or click to browse)
- Classify it: which song? what type? what source?
- Auto-extract metadata (duration, format, date)
- File is moved to the right directory automatically

#### Apple Notes Lyrics Import
Your Apple Notes database exists and is readable. Build a scanner that:
- Reads NoteStore.sqlite
- Surfaces notes that look like lyrics or song ideas
- Lets you link them to songs or create new ideas

### Medium Priority

#### Song Comparison View (covers)
Side-by-side player: original recording on the left, your version on the right. Aligned playback so you can A/B specific sections. Invaluable for improving covers.

#### Suno AI Integration
- Designated import folder or direct API integration
- Tag Suno-generated content distinctly
- Use Suno outputs as demos/references for originals you want to learn to play yourself

#### Export for Social Media
- Trim audio/video clips to specific time ranges
- Format conversion for Instagram Reels (vertical, <60s, AAC)
- Thumbnail generation from video frames
- One-click from content planner → export-ready file

#### Smart Setlist Suggestions
Based on your data:
- "You haven't played [song] in 3 weeks — add to practice?"
- "These 8 songs are all polished and in similar keys — good setlist?"
- Setlist gap analysis: "You need more upbeat songs" or "No songs in E"

#### Recommendation Engine
Uses your practice data, ratings, listening history, and repertoire to suggest:
- What to practice next (based on skill gaps, staleness, gig prep)
- What to learn (based on Apple Music listening, genre gaps, difficulty progression)
- What to improve (per-dimension rating trends, weak spots)
- Gig readiness assessment (setlist completeness, polish level)

#### Practice Progress & Analytics
- Rating trends per song and per dimension over time
- Practice frequency heatmap
- Most improved / needs attention highlights
- Skill radar chart (vocals, guitar, timing, etc.)
- Genre/key/tempo distribution analysis
- Session-over-session comparison

#### Apple Music Integration
- Import listening history from Apple Music local database
- Auto-suggest covers based on most-played songs
- Auto-link reference recordings from your library
- Genre/mood profiling from listening patterns

### Future

#### Gig & Venue Tracker
- Database of local venues and open mics (name, address, contact, vibe, pay)
- Event calendar: upcoming open mics, gig dates
- Gig history: what you played, where, how it went
- Eventually: community-sourced venue data for other musicians

#### Collaboration Hub
- Share songs/takes with bandmates (Sural, Greg)
- Collaborative notes and ratings
- Shared setlists for band gigs
- "Sural's mix vs. my mix" version comparison

#### Mobile App
- Phone-native recording → direct upload to Greenroom
- Quick idea capture (voice memo + tag)
- Setlist viewer for gig day
- Rate takes on the go after practice

#### Release Pipeline
- Master → upload to DistroKid → streaming platforms
- Track streaming stats
- Link released songs to their Greenroom history

---

## Data Architecture

### Song Types & Status Flows

```
Cover:    idea → learning → rehearsed → polished → recorded → released
Original: idea → draft → arranged → rehearsed → recorded → released
Idea:     captured → developing → promoted (graduates to original)
```

### Annotation System

**Ratings (per take, 1-5 stars):**
Overall, Vocals, Guitar, Drums, Tone, Timing, Energy

**Tags (on songs and takes):**
Predefined: needs-work, good-take, false-start, best-take, demo, final-mix, live-ready, needs-lyrics, needs-arrangement, crowd-pleaser, setlist-candidate, archived
Custom: user-created, any string

**Structured fields (per song):**
Key, Tempo (BPM), Tuning, Vibe

### Data Sources

| Source | Format | Ingestion |
|--------|--------|-----------|
| GoPro practice videos | MP4 | Session workflow (cut + extract) |
| Phone voice memos | M4A | Import / drag-drop |
| Phone video | MOV/MP4 | Import / drag-drop |
| Logic Pro exports | M4A/WAV | Import / drag-drop |
| GarageBand projects | .band → M4A | Manual export, then import |
| Suno AI | M4A/MP3 | Download → import folder |
| Collaborator (Sural) | M4A/MP3 | Shared → import |
| Backing tracks | MP3/MP4 | Download → import |
| Lyrics | Text | Paste in app / Apple Notes import |
| Reference recordings | MP3/M4A | Download → link to cover |

### File Storage

- **Primary:** Local filesystem (`~/Desktop/music/`)
- **Backup:** Cloud (TBD — iCloud, GCS, or Backblaze)
- **Future:** Cloud-primary for multi-device access
- **Paths:** Relative to music_dir in database, portable across machines

---

## Tech Stack

- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **Backend:** FastAPI + SQLAlchemy + SQLite
- **Media:** HTML5 audio/video via FastAPI FileResponse
- **Repo:** https://github.com/adamklie/greenroom

---

## Success Metrics (for Adam)

As a user, Greenroom is working when:
- [ ] I can find any recording in under 10 seconds
- [ ] I know exactly which songs are gig-ready
- [ ] I can see my progress over time
- [ ] I never lose a recording or idea
- [ ] Adding a new practice session takes < 5 minutes
- [ ] I post to social media at least once a week
- [ ] My bandmates can see what we're working on
- [ ] I have a setlist ready for any gig configuration (solo, duo, trio)
