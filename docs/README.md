# Greenroom Documentation

A private song-record-keeping app for working musicians. **FastAPI + SQLAlchemy + SQLite** backend, **React + TypeScript + Vite** frontend, deployed on **Fly.io** with **Cloudflare R2** for media. Magic-link auth, three roles (viewer/editor/admin). One Fly machine, one SQLite file, one container.

See the [main README](../README.md) for stack, costs, and quick start.

---

## Using the app

| Doc | For |
|---|---|
| [USER_GUIDE.md](USER_GUIDE.md) | What each page does. Common workflows. Recovery. |
| [DEMO_SCRIPT.md](DEMO_SCRIPT.md) | 10-min walkthrough to show someone the app. |

## Operating the deployment

| Doc | For |
|---|---|
| [DEPLOYMENT.md](DEPLOYMENT.md) | Fly + R2 + Resend setup. Secrets. First-deploy runbook. |
| [MIGRATIONS.md](MIGRATIONS.md) | Alembic conventions. How to ship a schema change. |
| [REMOVED.md](REMOVED.md) | Features cut during simplify-v2 and why. |

## Hacking on it

| Doc | For |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System map, request flows, boot sequence, code layout. Read first. |
| [SCHEMAS.md](SCHEMAS.md) | Table-by-table SQLAlchemy reference. |
| [DATA_INGESTION.md](DATA_INGESTION.md) | How source files become AudioFile rows. |
| [CONTRIBUTING.md](CONTRIBUTING.md) | PR cycle, principles, Explore → Plan → Code → Test. |
| [STYLE.md](STYLE.md) | How to write docs in this repo. |

## Active refactor

[AUDIOFILE_UNIFICATION.md](AUDIOFILE_UNIFICATION.md) — Take → AudioFile migration. Phases 1–3 done; Phase 4 (drop Take) open. Read before touching practice-session code.
</content>
