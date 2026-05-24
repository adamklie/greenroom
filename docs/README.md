# Greenroom Documentation

Greenroom is a private song-record-keeping app for working musicians —
covers, originals, ideas, with versioned audio, ratings, lyrics, tabs,
and setlists. See the [main README](../README.md) for the elevator pitch,
tech stack, and quick start.

This `docs/` tree is structured for a future mkdocs / readthedocs site.
Each file is a single-concept page; cross-links are relative so they
work locally, on GitHub, and in a generated site.

---

## If you're using the app

- [**USER_GUIDE.md**](USER_GUIDE.md) — what each page does, common
  workflows, what to do if something looks broken.
- [**DEMO_SCRIPT.md**](DEMO_SCRIPT.md) — 10-minute walkthrough for
  showing the app to a new user.

## If you're operating the deployment

- [**DEPLOYMENT.md**](DEPLOYMENT.md) — Fly + R2 + Resend setup, secrets,
  first-deploy runbook.
- [**MIGRATIONS.md**](MIGRATIONS.md) — Alembic conventions, applying
  schema changes, rollback strategy.
- [**REMOVED.md**](REMOVED.md) — features that were cut during
  simplification (Triage, Sync page, Discover, Recommendations, Apple
  Music ingest) and why.

## If you're hacking on it

- [**ARCHITECTURE.md**](ARCHITECTURE.md) — system map, request flow
  walkthroughs, boot sequence, storage layout, auth model, code layout,
  operational gotchas. The single source of truth for how the system is
  wired.
- [**SCHEMAS.md**](SCHEMAS.md) — table-by-table SQLAlchemy reference.
- [**DATA_INGESTION.md**](DATA_INGESTION.md) — how source files become
  AudioFile rows.
- [**CONTRIBUTING.md**](CONTRIBUTING.md) — principles, PR cycle,
  Explore → Plan → Code → Test workflow, Claude Code tooling.

## Active refactor

- [**AUDIOFILE_UNIFICATION.md**](AUDIOFILE_UNIFICATION.md) — ongoing
  Take → AudioFile migration. Phases 1–3 done; Phase 4 (drop Take table)
  pending. Read this before touching practice-session code.
