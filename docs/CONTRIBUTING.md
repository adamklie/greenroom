# Contributing to Greenroom

---

## Before you start

1. Read [VISION.md](VISION.md) — what Greenroom is, who it's for, the three pillars
2. Read [STORAGE.md](STORAGE.md) — how files + DB + backups are laid out
3. Skim [ROADMAP.md](ROADMAP.md) — what's built and what's next

---

## How we work

Greenroom is a solo project with Claude Code as the primary collaborator. There's no staging environment, no QA, no second reviewer. Every change needs to be **deliberate and precise** — the user is the only backstop.

### Principles

| Principle | In practice |
|-----------|-------------|
| **Stability** | Don't introduce bugs or fragile behavior. If something works, don't break it while trying to improve something else. |
| **Backwards compatibility** | Existing features must keep working. Changing an API endpoint, DB column, or data shape means checking every caller. |
| **Maintainability** | Write code that future-you (or a fresh Claude session) can understand. Clear names > clever tricks. Match the existing style. |
| **Precision** | Do the thing you set out to do. Don't clean up unrelated code, don't add speculative features, don't refactor while fixing a bug. |

### The workflow: Explore → Plan → Code → Test

For any non-trivial change:

**Explore** — Before writing code, read the files you'll be touching and the files that depend on them. Understand what exists and why.

**Plan** — What's the smallest change that achieves this? What could break? What callers depend on this code? If anything's unclear, ask before coding.

**Code** — Surgical changes. Match the style of the surrounding code. Don't refactor neighbors unless that's the explicit goal.

**Test** — Verify the change works AND verify nothing else broke. If something regresses, go back to planning — don't patch around it.

See [DEVELOPMENT_WORKFLOW.md](DEVELOPMENT_WORKFLOW.md) for the step-by-step version, including the Claude Code prompt template.

---

## Pull requests

### Keep them focused

**One concern per PR.** A PR that does one thing is easy to review, easy to merge, and easy to revert. A PR that does five things is hard to review, creates conflicts, and if one part is wrong you can't roll back without losing the other four.

Examples:
- Vault architecture = one PR
- Contributing docs + Claude tooling = a separate PR
- Feedback form bug fix = its own PR

### What to include in the description

- What you changed and why
- Anything a reviewer (even future-you) should know — edge cases, decisions you second-guessed, things you weren't sure about
- A short test plan — what you verified and what still needs interactive testing

### What NOT to commit

| Don't commit | Why | What to do instead |
|---|---|---|
| `backend/.venv/`, `frontend/node_modules/` | Build artifacts, regeneratable | Already in `.gitignore` |
| `greenroom.db`, `*.db` | Live DB — changes constantly, too large | Rolling backups live in the iCloud vault (see [STORAGE.md](STORAGE.md)) |
| `.env`, credentials, API keys | Security risk | `.env` locally (gitignored); env vars in deploys |
| Audio/video files | Not what git is for | Vault in iCloud is the canonical store |
| `frontend/dist/`, `__pycache__/`, `.DS_Store` | Build/OS noise | Already in `.gitignore` |

### Reviewing a PR

Before merging, check:

- Does the PR do **one** thing? (No unrelated changes mixed in)
- Does existing functionality still work?
- Is there dead code (new functions that nothing calls)?
- Are build artifacts or debug files included?
- Does it match the existing code style?

In Claude Code, `/review-pr <number>` runs an automated pass against these principles.

---

## Branching

Use descriptive branch names with a prefix:

| Prefix | When to use |
|--------|-------------|
| `feat/` | New features or capabilities |
| `fix/` | Bug fixes |
| `ui/` | Frontend-only / visual changes |
| `docs/` | Documentation |
| `refactor/` | Code reorganization with no behavior change |

---

## Key things to watch out for

### `CLAUDE.md` is not a README

The file called `CLAUDE.md` at the repo root is automatically read by Claude Code as project instructions — it's tooling config, not user-facing docs. Don't put general documentation, meeting notes, or marketing copy there. User-facing info goes in `docs/` or `README.md`.

### Frontend and backend are separate

The React frontend (`frontend/src/`) and FastAPI backend (`backend/app/`) communicate through API endpoints. If you're changing an endpoint shape, update both sides in the same PR — the typed API client in `frontend/src/api/client.ts` has to match the backend response.

### The vault is canonical

Audio/video files live in the iCloud vault as flat `{identifier}.{ext}` files. The DB path is just the filename. **Never** write code that infers file location from song metadata (project, title, artist) — resolution goes through `backend/app/services/vault.py`. See [STORAGE.md](STORAGE.md).

### The DB is the source of truth for metadata

Ratings, tags, lyrics, notes, song structure — all in the DB. The `exports/annotations_latest.json` and DB backups in the vault are the recovery path. Don't introduce code that relies on re-scanning the filesystem to rebuild metadata.

---

## Claude Code tooling

If you're using Claude Code in this repo, these slash commands are wired up (see [`.claude/skills/`](../.claude/skills/)):

| Command | What it does |
|---------|--------------|
| `/review-pr <number>` | Automated review of a PR against the principles above |

Hooks in [`.claude/hooks/`](../.claude/hooks/) also fire automatically:

- **check-large-files** (pre-Bash on `git add/commit`) — warns about files >50MB before they land in a commit
- **validate-python** (post-Edit/Write on `.py` files) — runs `python -m py_compile` to catch syntax errors immediately
