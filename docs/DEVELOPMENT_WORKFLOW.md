# Development Workflow

> Step-by-step process for making changes to Greenroom, whether coding by hand or driving Claude Code.

---

## Overview

Every non-trivial change follows this cycle:

```
Create PR → Develop (Explore → Plan → Code → Test) → Review → Merge
```

Each stage has a specific purpose. If you skip a stage — especially the plan approval — you end up with code that's technically correct but doesn't match what you wanted.

---

## Step 1: Create a draft PR with your idea

Before writing any code, create a branch and open a **draft** PR describing what you want to do. No code yet — just intent.

```bash
git checkout -b feat/my-feature
git push -u origin feat/my-feature
gh pr create --draft \
  --title "Short, specific title" \
  --body "What this will do and why, in 2–5 sentences."
```

**Why first?** It forces you to name the change, makes the scope visible before you're invested in code, and gives Claude Code a clear target.

---

## Step 2: Develop

The actual work. Follow **Explore → Plan → Code → Test**.

### If using Claude Code

Start the session by loading context, then hand over the PR:

```
Read docs/CONTRIBUTING.md, docs/VISION.md, and docs/STORAGE.md. Then read
the PR description for PR #<number>.

Follow the Explore → Plan → Code → Test workflow:
  1. Explore: list the files relevant to this change and read them
  2. Plan: write a short plan — what you'll change, what could break,
     open questions — and pause for my approval before writing code
  3. Code: implement the plan with surgical, targeted changes
  4. Test: verify it works and nothing else broke
```

**Key beats during development:**

| Stage | What Claude Code should do | What you should do |
|-------|----------------------------|---------------------|
| Explore | Read relevant files, find callers, identify deps | Spot-check the file list — anything missing? |
| Plan | Write a short plan, flag risks, ask questions | **Approve before coding.** Your chance to redirect. |
| Code | Minimal, precise changes matching existing style | Review diffs as they appear |
| Test | Type-check, smoke-test, hit endpoints with curl | Click through the UI for anything visual |

**The plan approval step is the most important one.** Five minutes reviewing a plan saves an hour of rework.

### If coding by hand

Same cycle, just in your head:
1. Read the code you'll touch
2. Think through the change before starting
3. Make it
4. Verify

---

## Step 3: Review

Before flipping the PR from draft to ready (or before merging), run a review pass.

### Using Claude Code

```
/review-pr <number>
```

This checks for:

- **Stability** — syntax errors, missing null checks, deeply nested logic
- **Backwards compatibility** — orphaned functions, changed response shapes, unused-but-exported code
- **Precision** — dead code, scope creep, build artifacts committed
- **Maintainability** — unclear names, duplicated code, missing error messages

Output: findings classified as **CRITICAL** (must fix), **WARNING** (should fix), or **NOTE** (nice to fix).

### Manual review checklist

If not using Claude Code:

- [ ] PR does one thing — no unrelated changes mixed in
- [ ] Build artifacts excluded (`dist/`, compiled JS, `.pyc`, `.db`)
- [ ] Existing functionality still works (run the app, try a couple flows)
- [ ] No new functions without callers (dead code)
- [ ] Code is clear enough to maintain six months from now

---

## Step 4: Fix and merge

If review found issues:
1. Fix on the same branch
2. Push
3. Re-run `/review-pr` to confirm resolved
4. Mark PR "ready for review" (out of draft)
5. Merge (squash or regular — your call)

If review was clean: mark ready, merge.

---

## Quick reference

| When | What to do | Claude Code command |
|------|-----------|---------------------|
| Starting a new feature | Open a draft PR with description | — |
| Starting development | Give Claude the PR context + workflow prompt | See Step 2 |
| Plan is ready | Review and approve before code starts | — |
| Code is done | Run automated review | `/review-pr <number>` |
| Review is clean | Mark ready, merge | — |

---

## Principles reminder

These apply to every change, no matter how small:

- **Stability** — Don't introduce bugs or fragile behavior
- **Backwards compatibility** — Existing features must keep working
- **Maintainability** — Write code others can understand
- **Precision** — Do the thing you set out to do, nothing more

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full contributing guide.
