# Greenroom — Product Vision

Last updated: 2026-05-23

## What Greenroom Is

A song record-keeping tool for working musicians. One central place to organize, annotate, and find your music — covers, originals, and ideas — with standardized, machine-readable data that helps you track progress and prepare for gigs.

The unit of work is the **song row**. Everything else (audio files, takes, tabs, lyrics, ratings, setlist entries) hangs off it. Anything that isn't in service of "edit a song row, attach a recording, rate it, find it later" is out of scope.

## Who It's For

Musicians who:
- Play covers and write originals
- Practice regularly (solo and with bands)
- Record on various devices (phone, GoPro, DAW)
- Play open mics and local gigs
- Have music scattered across devices, apps, and folders

## The Three Pillars

### 1. Covers
Every cover is tracked through its stages — first attempt through gig-ready. Status, ratings, and tags make it queryable.

### 2. Originals
Your own songs, tracked from initial idea through arrangement, rehearsal, recording. Version history shows how a song evolves. Notes capture decisions ("Sural wants the bridge in A minor").

### 3. Ideas
A bank of raw material — voice memos, riff recordings, lyric fragments. Nothing gets lost. Ideas can be promoted to originals when they're ready to develop.

## Tabs

Every song can carry one or more Guitar Pro tab files (`.gp`, `.gp3`–`.gp7`, `.gpx`), uploaded and rendered inline via alphaTab. Tabs sit alongside recordings and lyrics as a first-class part of each song.

## Core Principles

1. **Standardized and machine-readable.** Every piece of data has structure — typed fields, tags, ratings, not just free-text blobs. This makes everything queryable: "show me all covers in Am that are gig-ready."

2. **Workflow-first.** Every feature maps to how you actually practice, record, and find music. The app adapts to your process, not the other way around.

3. **Nothing gets lost.** Every recording, every idea, every lyric — captured and findable. The triage system catches files that fall through the cracks.

4. **Progress is visible.** You can see yourself improving over time through ratings, practice frequency, and version history.

## Success Metrics

Greenroom is working when:
- [ ] I can find any recording in under 10 seconds
- [ ] I know exactly which songs are gig-ready
- [ ] I can see my progress over time
- [ ] I never lose a recording or idea
- [ ] Adding a new practice session takes < 5 minutes
- [ ] I have a setlist ready for any gig configuration (solo, duo, trio)

## Removed in MVP 1.0

The following lived in earlier iterations but were cut as out-of-scope for "song record-keeping" (see [REMOVED.md](../REMOVED.md)):

- Content Planner (social-media post kanban)
- Discover / Apple Music ingestion + suggestions
- Recommendations engine
- Dedup admin UI
- Reorganize admin UI
- Roadmap parser (career-stage checklists)

---

## Related Docs

- [ARCHITECTURE.md](ARCHITECTURE.md) — system map, request flows, boot sequence
- [USER_GUIDE.md](USER_GUIDE.md) — what each page does, workflows, backups
- [DEMO_SCRIPT.md](DEMO_SCRIPT.md) — 10-min walkthrough for new users
- [DEPLOYMENT.md](DEPLOYMENT.md) — Fly + R2 + Resend setup
- [SCHEMAS.md](SCHEMAS.md) — DB schema, status flows, annotation system
- [STORAGE.md](STORAGE.md) — filesystem layout and backups
- [DATA_INGESTION.md](DATA_INGESTION.md) — how data sources enter the system
- [AUDIOFILE_UNIFICATION.md](AUDIOFILE_UNIFICATION.md) — Take → AudioFile refactor (Phase 4 open)
- [../README.md](../README.md) — tech stack and setup
- [../REMOVED.md](../REMOVED.md) — features cut during simplification
