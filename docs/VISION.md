# Greenroom — Product Vision

Last updated: 2026-04-16

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

## Tabs

Every song can carry one or more Guitar Pro tab files (`.gp`, `.gp3`–`.gp7`, `.gpx`), uploaded and rendered inline via alphaTab. Tabs sit alongside recordings and lyrics as a first-class part of each song — so practice, learning, and performance all happen in one place.

## Core Principles

1. **Standardized and machine-readable.** Every piece of data has structure — typed fields, tags, ratings, not just free-text blobs. This makes everything queryable: "show me all covers in Am that are gig-ready."

2. **Workflow-first.** Every feature maps to how you actually practice, record, and perform. The app adapts to your process, not the other way around.

3. **Nothing gets lost.** Every recording, every idea, every lyric — captured and findable. The triage system catches files that fall through the cracks.

4. **Progress is visible.** You can see yourself improving over time through ratings, practice frequency, and version history.

## Success Metrics

Greenroom is working when:
- [ ] I can find any recording in under 10 seconds
- [ ] I know exactly which songs are gig-ready
- [ ] I can see my progress over time
- [ ] I never lose a recording or idea
- [ ] Adding a new practice session takes < 5 minutes
- [ ] I post to social media at least once a week
- [ ] My bandmates can see what we're working on
- [ ] I have a setlist ready for any gig configuration (solo, duo, trio)

---

## Related Docs

- [ROADMAP.md](ROADMAP.md) — built, in-progress, and planned features
- [SCHEMAS.md](SCHEMAS.md) — DB schema, status flows, annotation system
- [STORAGE.md](STORAGE.md) — filesystem layout and backups
- [DATA_INGESTION.md](DATA_INGESTION.md) — how data sources enter the system
- [AUDIOFILE_UNIFICATION.md](AUDIOFILE_UNIFICATION.md) — unified audio file model
- [ANALYTICS.md](ANALYTICS.md) — metrics and analytics endpoints
- [../README.md](../README.md) — tech stack and setup
