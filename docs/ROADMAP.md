# Greenroom — Roadmap

Last updated: 2026-04-16

Current and planned features. For the product thesis, see [VISION.md](VISION.md).

## Built ✓

### Song organization
- [x] Three-pillar song organization (covers/originals/ideas)
- [x] Structured music fields (key, tempo, tuning, vibe)
- [x] Multi-dimensional ratings (overall, vocals, guitar, drums, tone, timing, energy)
- [x] Tags system (predefined + custom, on songs and takes)
- [x] Lyrics editor with version history
- [x] Guitar Pro tab upload + inline rendering (alphaTab)
- [x] Inline editing of all song metadata (reclassify, rename, reassign)
- [x] Idea → Original promotion

### Practice & sessions
- [x] Practice session browser with 273 takes across 28 sessions
- [x] Audio playback in-browser for all recordings
- [x] GoPro session workflow (Process page): timeline scrub, mark cut points, assign to songs, one-click cut + audio extract + take creation
- [x] Practice progress visualization (Progress page): rating trends, practice frequency, per-dimension analysis

### Library & files
- [x] Unified Library view across all audio files (605 rows)
- [x] Triage queue for unclassified files (129 items)
- [x] File health check (detect broken links)
- [x] File consolidation (pull scattered files into organized directory)
- [x] Filesystem bootstrap (scans ~/Desktop/music, ~/Music, ~/Desktop)
- [x] Rescan button for live filesystem updates
- [x] Import page for drag-and-drop classification of new recordings
- [x] Dedup + reorganize tools

### Apple Music integration
- [x] Listening history ingestion (391k plays, 413 playlists)
- [x] Discover page surfacing listening patterns and cover candidates
- [x] Recommendations engine backed by listening + practice data

### Performance & gigs
- [x] Setlist builder with running time
- [x] Social media content planner (kanban: planned → ready → posted)

### App-wide
- [x] Dashboard with portfolio stats
- [x] Sync workflow (rescan → hash → health → export → DB backup → git commit/push)
- [x] In-app Feedback → GitHub issues
- [x] Settings page
- [x] Dark/light mode

## Next Up — High Impact

### Apple Notes Lyrics Import
Your Apple Notes database exists and is readable. Build a scanner that:
- Reads NoteStore.sqlite
- Surfaces notes that look like lyrics or song ideas
- Lets you link them to songs or create new ideas

### Song Comparison View (covers)
Side-by-side player: original recording on the left, your version on the right. Aligned playback so you can A/B specific sections. Invaluable for improving covers.

### Export for Social Media
- Trim audio/video clips to specific time ranges
- Format conversion for Instagram Reels (vertical, <60s, AAC)
- Thumbnail generation from video frames
- One-click from content planner → export-ready file

## Medium Priority

### Suno AI Integration
- Designated import folder or direct API integration
- Tag Suno-generated content distinctly
- Use Suno outputs as demos/references for originals you want to learn to play yourself

### Smart Setlist Suggestions
Based on your data:
- "You haven't played [song] in 3 weeks — add to practice?"
- "These 8 songs are all polished and in similar keys — good setlist?"
- Setlist gap analysis: "You need more upbeat songs" or "No songs in E"

### Deeper Practice Analytics
- Skill radar chart (vocals, guitar, timing, etc.)
- Genre/key/tempo distribution analysis
- Session-over-session comparison
- Gig readiness assessment (setlist completeness, polish level)

## Future

### Gig & Venue Tracker
- Database of local venues and open mics (name, address, contact, vibe, pay)
- Event calendar: upcoming open mics, gig dates
- Gig history: what you played, where, how it went
- Eventually: community-sourced venue data for other musicians

### Collaboration Hub
- Share songs/takes with bandmates (Sural, Greg)
- Collaborative notes and ratings
- Shared setlists for band gigs
- "Sural's mix vs. my mix" version comparison

### Mobile App
- Phone-native recording → direct upload to Greenroom
- Quick idea capture (voice memo + tag)
- Setlist viewer for gig day
- Rate takes on the go after practice

### Release Pipeline
- Master → upload to DistroKid → streaming platforms
- Track streaming stats
- Link released songs to their Greenroom history
