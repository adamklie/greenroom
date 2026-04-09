# Greenroom Analytics & Recommendations

Last updated: 2026-04-08

## Overview

Greenroom collects structured, machine-readable data about your music practice, recordings, and portfolio. This document describes how that data is analyzed to generate recommendations and insights.

## Data Available for Analysis

### Practice Data
- **224 takes** across **21 sessions** (June 2025 — March 2026)
- 7-dimension ratings per take: overall, vocals, guitar, drums, tone, timing, energy
- Tags per take: good-take, needs-work, false-start, etc.
- Timestamps: when each session occurred, which songs were played
- Audio recordings: playable for qualitative review

### Song Portfolio
- **108 songs**: 50 covers, 48 originals, 10 ideas
- Status tracking: idea → learning → rehearsed → polished → recorded → released
- Structured fields: key, tempo, tuning, vibe
- Practice frequency: how many sessions include each song
- Tags: live-ready, crowd-pleaser, setlist-candidate, etc.

### Recordings
- **186 audio files** across all sources
- Version tracking: v1, v2, v3 iterations
- Source tracking: GoPro, phone, Logic Pro, GarageBand, Suno AI, collaborator

### Future: Apple Music Listening History
- Play counts per song
- Listening frequency and recency
- Artist/genre preferences
- Discovery patterns

## Recommendation Engine

### Current Recommendations (v1)

The engine at `GET /api/recommendations` generates recommendations from 7 analyzers:

| Analyzer | What It Does | Example Output |
|----------|-------------|----------------|
| **Stale Songs** | Finds songs not practiced recently | "Refresh: Float On — last practiced 66 days ago" |
| **Skill Gaps** | Compares rating dimensions | "Focus on vocals — averaging 2.3/5 vs guitar at 4.1/5" |
| **Unrated Takes** | Nudges rating adoption | "Rate your takes (224 unrated)" |
| **Gig Readiness** | Assesses setlist completeness | "Solo set: need 8 more polished songs" |
| **Repertoire Gaps** | Analyzes key/type distribution | "Add keys to 108 songs" |
| **Idea Review** | Surfaces stale ideas | "Review 5 old ideas — promote or archive" |
| **Recording Candidates** | Finds polished but unrecorded songs | "Record: Your Touch — it's polished and ready" |

### Priority Levels
- **High (red):** Actionable now, blocking progress
- **Medium (yellow):** Important but not urgent
- **Low (green):** Nice to do, quality of life

### How Recommendations Improve Over Time

The more you use Greenroom, the better recommendations get:
1. **Rate your takes** → unlocks skill gap analysis
2. **Set song keys/tempos** → unlocks repertoire gap analysis
3. **Use status tracking** → unlocks gig readiness assessment
4. **Practice consistently** → unlocks staleness detection and progress trends
5. **Import Apple Music** → unlocks cover suggestions and genre profiling

## Planned Analytics Features

### Practice Progress Charts
- **Rating trend lines**: per song and per dimension, over time
- **Practice frequency heatmap**: calendar view of when you played
- **Session comparison**: side-by-side rating distributions across sessions
- **Most improved**: songs with biggest rating increases
- **Needs attention**: songs with declining or stagnant ratings

### Skill Radar Chart
Spider/radar visualization of your average ratings across all 7 dimensions. Shows strengths and weaknesses at a glance. Track how the shape changes over months.

### Repertoire Analytics
- **Key distribution**: pie chart of song keys (find gaps)
- **Tempo distribution**: histogram of BPMs (find your sweet spot)
- **Genre spread**: based on artist/vibe tags
- **Cover vs. original ratio**: over time
- **Status funnel**: how many songs at each stage

### Apple Music Integration Analytics
- **Listening → Playing pipeline**: songs you listen to most that you haven't covered
- **Genre alignment**: does what you play match what you listen to?
- **Discovery rate**: how quickly new listens become new covers
- **Artist deep-dive**: "You've listened to 200 Weezer songs but only cover 3"

### Gig Analytics (future)
- **Setlist optimization**: suggest set order based on key changes, energy flow
- **Gig history**: what you played where, audience response
- **Revenue tracking**: pay per gig over time
- **Venue compatibility**: which venues suit your style

## Technical Implementation

### Recommendation Engine Architecture

```
GET /api/recommendations
    │
    ├── _stale_songs(db)          → practice recency analysis
    ├── _skill_gaps(db)           → multi-dimension rating comparison
    ├── _unrated_takes(db)        → adoption nudge
    ├── _gig_readiness(db)        → setlist completeness
    ├── _repertoire_gaps(db)      → key/genre/type distribution
    ├── _idea_review(db)          → stale idea detection
    └── _recording_candidates(db) → polished → recorded pipeline
    │
    └── Sort by priority → return list[Recommendation]
```

Each analyzer is a pure function that takes a DB session and returns a list of `Recommendation` objects. New analyzers can be added independently.

### Data Model for Analytics

All analytics are computed from existing tables — no separate analytics store needed:

```sql
-- Practice frequency: GROUP BY date, song_id on takes+sessions
-- Rating trends: ORDER BY session.date, filter by song_id
-- Skill gaps: AVG(rating_*) across all takes
-- Repertoire: GROUP BY key, type, project on songs
-- Staleness: MAX(session.date) per song vs today
```

### Future: Time-Series Storage

For long-term trend analysis, we may want to snapshot aggregate stats periodically:

```sql
CREATE TABLE analytics_snapshots (
    id INTEGER PRIMARY KEY,
    snapshot_date DATE NOT NULL,
    metric_name TEXT NOT NULL,    -- 'avg_rating_vocals', 'total_polished_songs', etc.
    metric_value REAL NOT NULL,
    metadata TEXT                 -- JSON for additional context
);
```

This enables "3 months ago your average vocal rating was 2.1, now it's 3.4" without replaying all historical data.
