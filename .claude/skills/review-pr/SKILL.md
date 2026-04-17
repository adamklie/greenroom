---
description: Review a GitHub PR for principle violations and propose fixes. Usage: /review-pr <pr-number>
---

# /review-pr

Review a pull request against Greenroom's four principles (Stability, Backwards Compatibility, Maintainability, Precision — see `docs/CONTRIBUTING.md`), then propose fixes.

## Instructions

Given a PR number, perform a two-phase review.

### Phase 1: Detect

1. Fetch the PR and the diff:
   ```
   gh pr view $ARGUMENTS --json title,body,files,additions,deletions
   gh pr diff $ARGUMENTS
   ```

2. Launch parallel agents to check:

   **Agent 1 — Backwards Compatibility:**
   - Functions/exports removed but still called elsewhere in the repo
   - New required parameters without backwards-compatible defaults
   - Changed API response shapes (`backend/app/routers/*`) that the frontend client (`frontend/src/api/client.ts`) still expects in the old shape
   - DB schema changes without a migration path for existing rows (Greenroom's DB is user state, not throwaway)

   **Agent 2 — Stability:**
   - Python syntax / import errors (`python -m py_compile` on changed files)
   - TypeScript errors (`cd frontend && npx tsc --noEmit`)
   - Missing null/undefined checks, especially on DB queries that return `None` for missing IDs
   - Functions over ~50 lines or deeply nested logic that's hard to reason about
   - Filesystem writes outside the vault or the repo — check for `music_dir` / `vault_dir` misuse

   **Agent 3 — Precision:**
   - Dead code: new functions with zero callers (grep across `backend/` and `frontend/`)
   - Scope creep: changes in files unrelated to the PR's stated purpose
   - Build artifacts or debug files committed (`node_modules/`, `dist/`, `__pycache__/`, `*.db`, `.env`)
   - Audio/video files checked into git (should be in the iCloud vault; see `docs/STORAGE.md`)

   **Agent 4 — Maintainability:**
   - Unclear variable names or logic
   - Missing error messages on HTTPException / raised errors
   - Duplicated code that could be consolidated (especially path resolution — should flow through `backend/app/services/vault.py`)
   - New comments that explain *what* the code does (which the code already shows) rather than *why*

3. Classify each finding:
   - **CRITICAL**: Will break production (syntax errors, removed functionality with live callers, committed credentials, schema changes that break existing rows)
   - **WARNING**: Should fix before merge (dead code, scope creep, missing tests for new behavior)
   - **NOTE**: Nice to fix, not blocking (naming, minor style)

### Phase 2: Validate & Propose Fixes

For each finding:
1. Verify with evidence — grep output, type-check result, quoted diff snippet
2. Classify as CONFIRMED or FALSE POSITIVE
3. Propose a **principle-aligned** solution:
   - Prefer **integration** over deletion
   - Prefer **forking with optional params** over breaking changes
   - Prefer **incremental changes** over rewrites
   - Don't suggest deleting code without grepping for callers first

### Output Format

```markdown
# PR #<number> Review

## Summary
**Title**: <PR title>
**Files changed**: <N>
**Violations**: <total> (<critical> critical, <warning> warning, <note> note)
**Recommendation**: 🔴 REQUEST CHANGES / 🟡 APPROVE WITH NOTES / 🟢 APPROVE

---

## Issues

### 🔴 <Critical Issue Title>
**Location**: `path/to/file.py:123`
**Principle**: Backwards Compatibility
**Problem**: <one sentence>
**Evidence**: <grep output / diff snippet>
**Fix**: <proposed solution, with code if needed>

### 🟡 <Warning Title>
...

### 🔵 <Note Title>
...

---

## Checklist
- [ ] [must fix] <short description> — `file:line`
- [ ] [should fix] <short description> — `file:line`
```

### Rules

- Never suggest deleting code without verifying it's truly unused — grep the whole repo for callers
- If a function was removed from one call site, check **all** call sites (backend routers, frontend pages, services, scripts/)
- Backwards compatibility applies to the API too — if a response shape changed, check `frontend/src/api/client.ts` and every page that consumes it
- Filesystem writes should land in the vault (via `ingest_into_vault`) or in controlled locations (tempfiles, backups). Writes to arbitrary paths in `music_dir` or outside the repo are a flag.
- `file_path` columns should round-trip through `resolve_audio_path` (the vault-first resolver). Raw `music_dir / file_path` is legacy — flag it in new code.
