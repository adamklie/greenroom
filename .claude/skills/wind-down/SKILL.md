---
description: Wind down and safely exit a GaiusTx session — verify nothing is half-done, then update every artifact a fresh session needs to resume (HANDOFF, TODAY.md, memory, any drifted docs). Run at the end of a session, or when the user asks "is it safe to exit", "wind down", "end the session", or "hand off". Usage: /wind-down
---

# /wind-down

The session-exit bookend to `/today`. Goal: a new session (or another agent) can pick up **exactly** where this one left off — nothing uncommitted, nothing undocumented, no half-finished state hiding.

## Steps

1. **Identify the active scope.** Which repo(s)/project(s) did this session actually touch (e.g. `projects/<name>`, `public-data/<…>`, `gstudio`, a tool)? Run the remaining steps per active repo. If unsure, ask the user to confirm the scope.

2. **Surface uncommitted / half-done work.** For each active repo: `git status --short`, `git log --oneline -5`, and note the branch (`git branch --show-current`). Flag **anything** uncommitted, staged-but-not-committed, or partially-edited. Never let the session end with silent uncommitted work — either commit it (only if the user asked or it's a clean checkpoint) or list it explicitly so the next session sees it. Call out non-default branches and any work that spans repos.

3. **Run the project's checks.** If the project has gates/tests (validation scripts, `verify_quotes`/`lint`, `pytest`, `/validate`, a build), run them and report **green/red plainly**. If red, say so — do not paper over it. Record the exact command so the next session can re-run it.

4. **Update the handoff doc.** Update (or create) the project's `HANDOFF.md` so it reads TRUE for a cold start: current state, what changed this session, what's open, the **single next concrete action**, residuals + who owns each, and the key commands/paths. **Reconcile drifted sections — don't just append.** Reference commits/docs by path; don't duplicate them. (Reuse `/handoff` to seed the conversation summary if helpful.)

5. **Update TODAY.md.** Append this session's completed items to `archive/TODO.md`; keep only carryover + open items in `TODAY.md`, each with a one-line "where it stands" so `/today` resumes cleanly tomorrow.

6. **Persist memory.** Write session outcomes/decisions to the file-based memory (`memory/project_<name>.md` + a `MEMORY.md` pointer): what changed, decisions locked (with the why), residuals. Update an existing memory file rather than duplicating; delete memories this session proved wrong. Convert relative dates to absolute.

7. **Sweep drifted docs.** Flag (or fix) docs that went stale this session — READMEs, `CLAUDE.md`, schema/convention notes, skill indexes. If many drifted, run/suggest `/sync-docs`. If an org-level milestone landed (new repo, tool version, workflow), prompt `/changelog`.

8. **Report the exit verdict.** A tight "state of play": what changed, what's committed (commit hashes), what's open, the one next action, and an explicit **Safe to exit: yes / no** — with any residual that is **not yet durable** named outright (uncommitted work, a red gate, data not yet pushed to GCS, a dependency on another owner).

## Rules

- This skill WRITES (HANDOFF / TODAY / memory). **Commit only when the user asks**; otherwise leave changes staged/listed and say so. Never assume a remote exists — verify with `git remote -v` before pushing.
- **Be honest about residuals.** Surface red gates, uncommitted work, non-default branches, and not-yet-durable data. Never declare "safe to exit" while something is half-done — say what's left instead.
- **Reconcile, don't just append** — fix the stale parts of HANDOFF/docs so a cold start reads true (a half-updated handoff is worse than none).
- Don't duplicate content that lives in commits/docs/memory; point at it.
- Reuse the bookends and helpers: `/handoff` (conversation → doc), `/sync-docs` (doc staleness), `/changelog` (milestones), `/today` (the resume side this feeds).
- Follow the org file-op rules: list any moves/deletes before doing them; exclude junk.
