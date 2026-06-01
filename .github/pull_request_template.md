<!-- greenroom is live at greenroom-1.fly.dev and shared with the band. main is
     branch-protected; this PR + CI must pass before merge, then a manual deploy. -->

## What & why


## Deployment compatibility
Greenroom runs in **cloud/R2 mode** in prod (local dev is `local` mode). Most regressions come from local-only assumptions — confirm each:

- [ ] Works in **cloud / R2 mode**, not just local (no assumptions that files live on the local filesystem; media is keyed `files/{identifier}.{ext}` in R2)
- [ ] If the schema changed: an **Alembic migration is included and idempotent** (safe to run on a DB that may already have the change)
- [ ] No new env var / Fly secret required — or it's listed here and set with `fly secrets set`
- [ ] **Backward-compatible** with existing prod data (does not require a DB cutover; prod is the source of truth)
- [ ] CI green: `backend`, `frontend`, `backend-tests`

## How it was tested


## Release notes
<!-- One or two lines for the release tag / changelog -->

---
🤖 Generated with [Claude Code](https://claude.com/claude-code)
