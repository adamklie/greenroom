# Releasing

How changes get from a working branch to the live, band-facing app at
**greenroom-1.fly.dev**. Since real people use it, every change is reviewed and
CI-gated — there are no direct pushes to `main`.

See [DEPLOYMENT.md](DEPLOYMENT.md) for the underlying Fly/R2/Litestream runbook.

---

## The flow

```
branch  →  PR  →  CI green  →  review  →  merge to main  →  fly deploy  →  verify  →  tag
```

1. **Branch** off `main` (`feat/…`, `fix/…`, `chore/…`). Never commit to `main` — it's branch-protected (`enforce_admins: true`), so a direct push is rejected for everyone, including admins.
2. **Open a PR.** The template prompts the **deployment-compatibility checklist** — fill it in. The biggest risk is local-only assumptions that break in cloud/R2 mode.
3. **CI must pass** — three required checks: `backend`, `frontend`, `backend-tests`. The branch must also be up to date with `main`.
4. **Review** for correctness *and* deployment compatibility before merging.
5. **Merge** to `main` (squash). No approving review is *required* (solo-friendly), but CI + the checklist gate it.
6. **Deploy** (manual — merging does not auto-deploy):
   ```bash
   git checkout main && git pull
   fly deploy -a greenroom-1
   ```
   Alembic migrations run automatically on boot.
7. **Verify:** `curl https://greenroom-1.fly.dev/api/health` and a quick smoke test of the change.
8. **Tag the release** so we can roll back to a known-good point:
   ```bash
   git tag v0.3.0 && git push origin v0.3.0
   ```

## Data vs. schema vs. media

- **Content** (ratings, song links, new songs, users) — runtime writes to the prod DB. **No deploy.** Prod is the single source of truth; edit/create only in prod.
- **Schema change** (new column/table) — needs a PR with an **idempotent Alembic migration**, then a deploy. The migration runs on boot.
- **New media** — uploaded + processed in prod (browser→R2, cloud ffmpeg). The local→prod "DB cutover" in DEPLOYMENT.md is **disaster-recovery only** now; it overwrites prod and would clobber edits.

## Rolling back

- **Code:** `fly releases -a greenroom-1`, then redeploy the previous image (see DEPLOYMENT.md → "Rolling back a bad deploy").
- **Data:** Litestream point-in-time restore (see ARCHITECTURE.md).
