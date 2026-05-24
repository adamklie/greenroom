# Contributing to Greenroom

---

## Before you start

1. Read the root [README.md](../README.md) — what Greenroom is, tech stack, quick start
2. Read [ARCHITECTURE.md](ARCHITECTURE.md) — system map, request flows, boot sequence, storage layout, auth model

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

### The PR cycle

Every non-trivial change follows this loop:

```
Create draft PR → Develop (Explore → Plan → Code → Test) → Review → Merge
```

1. **Open a draft PR first**, before writing code. Name the change, scope it visibly, give Claude a clear target.
   ```bash
   git checkout -b feat/my-feature
   git push -u origin feat/my-feature
   gh pr create --draft --title "Short, specific" --body "What + why in 2-5 sentences."
   ```
2. **Develop** through Explore → Plan → Code → Test. The plan-approval step is the most important: five minutes reviewing a plan saves an hour of rework. Don't skip past `plan` when driving Claude.
3. **Review** before flipping out of draft. In Claude Code, `/review-pr <number>` runs an automated pass classifying findings as CRITICAL / WARNING / NOTE. Manual checklist: PR does one thing, no build artifacts, no dead code, no orphaned exports.
4. **Fix and merge.** Either squash or regular merge — your call.

### Driving Claude Code

When handing a PR to Claude, give it the workflow explicitly so it doesn't skip steps:

```
Read docs/CONTRIBUTING.md and docs/ARCHITECTURE.md. Then read PR #<number>.

Follow Explore → Plan → Code → Test:
  1. Explore: list and read the relevant files
  2. Plan: write a short plan — changes, risks, open questions — and PAUSE for approval
  3. Code: surgical, targeted changes only
  4. Test: pytest + manual smoke; verify nothing else broke
```

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
| `greenroom.db`, `*.db` | Live DB — changes constantly, too large | Rolling backups live in the iCloud vault (see [ARCHITECTURE.md](ARCHITECTURE.md#disaster-recovery-local-mode-new-machine)) |
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

Audio/video files live in the iCloud vault (local mode) or R2 (cloud) as flat `{identifier}.{ext}` files. The DB path is just the filename. **Never** write code that infers file location from song metadata (project, title, artist) — resolution goes through `backend/app/services/vault.py`. See [ARCHITECTURE.md](ARCHITECTURE.md#5-storage-layout).

### The DB is the source of truth for metadata

Ratings, tags, lyrics, notes, song structure — all in the DB. Recovery paths in order of recency: Litestream WAL replicas in R2 (continuous, 30-day retention), Fly volume daily snapshots, startup snapshots at `/data/vault/backups/` (last 10), and `Settings → Export JSON` in the running app (manual, on-demand). Don't introduce code that relies on re-scanning the filesystem to rebuild metadata.

---

## Claude Code tooling

If you're using Claude Code in this repo, these slash commands are wired up (see [`.claude/skills/`](../.claude/skills/)):

| Command | What it does |
|---------|--------------|
| `/review-pr <number>` | Automated review of a PR against the principles above |

Hooks in [`.claude/hooks/`](../.claude/hooks/) also fire automatically:

- **check-large-files** (pre-Bash on `git add/commit`) — warns about files >50MB before they land in a commit
- **validate-python** (post-Edit/Write on `.py` files) — runs `python -m py_compile` to catch syntax errors immediately
