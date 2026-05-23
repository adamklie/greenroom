---
description: Diagnose why the greenroom backend or frontend is misbehaving — check ports, tail logs, hit health endpoints, classify against known pitfalls. Triggers on "the app isn't loading", "500 error", "backend won't start", "vite is broken", "check the logs". Usage: /debug-servers
---

# /debug-servers

Diagnostic-first triage for a broken local dev environment. **Read-only by default** — don't edit files or restart servers unless the user explicitly confirms after seeing the diagnosis.

## Allowed tools

`Bash` (lsof, tail, curl, ls only) and `Read`. **Not** Edit, Write, or process-management commands without explicit user confirmation.

## Instructions

### 1. Check what's listening

```bash
lsof -i:8000
lsof -i:5175
```

Expected: backend (uvicorn / python) on :8000, vite (node) on :5175. Capture both PIDs.

If a port is empty, that server is down — note which one and continue.

### 2. Tail the logs

```bash
tail -n 100 /tmp/greenroom-backend.log
tail -n 100 /tmp/greenroom-frontend.log
```

Skim for stack traces, ImportError, SyntaxError, EADDRINUSE, MODULE_NOT_FOUND, ECONNREFUSED. Quote the most recent error verbatim in the diagnosis.

### 3. Hit the backend health endpoints

```bash
curl -s -m 3 -w "\nHTTP %{http_code}\n" http://localhost:8000/api/health
curl -s -m 3 -w "\nHTTP %{http_code}\n" http://localhost:8000/api/dashboard
```

`/api/health` should return `{"status": "ok", ...}` — if it times out, the backend isn't responsive even though the port is bound. `/api/dashboard` exercises the DB, so a 500 here often means a schema mismatch or vault path issue.

### 4. Report structured diagnosis

Output exactly this shape so the user can act fast:

```
## Diagnosis

**Backend (:8000):** <UP / DOWN / DEGRADED>
**Frontend (:5175):** <UP / DOWN / DEGRADED>

**Hot error:**
<verbatim quote of the most recent error from logs, or "none">

**Likely cause:** <one sentence>

**Suggested fix:** <one sentence, mapping to a known pitfall if it matches>
```

Then STOP. Wait for the user to confirm before running any fix.

## Known pitfalls

Match the hot error against these patterns. If you see X, try Y:

- **`504 Outdated Optimize Dep` in the frontend log or browser** → Vite's optimized-deps cache is stale. Fix: `rm -rf frontend/node_modules/.vite && bash dev.sh`.
- **`sqlite3.OperationalError: database is locked`** → the auto-backup thread (started in `app/main.py` lifespan) is racing with a query. Fix: wait 30s and retry, or `pkill -f backup_database` if it's wedged.
- **CORS errors in the browser console** (e.g. `has been blocked by CORS policy`) → the frontend is on a port not in `app.main`'s `allow_origins`. Currently allowed: `:5173`, `:5175`, `:5176`. Fix: switch frontend to an allowed port (`dev.sh` uses :5175) or add the port to the CORS list in `backend/app/main.py`.
- **`ModuleNotFoundError: No module named 'app'`** → uvicorn was started from the wrong cwd. Fix: always `cd backend && uvicorn app.main:app ...` — never run from repo root.
- **`.icloud` placeholder files appearing in the music dir** → iCloud has evicted those files. Fix: `brctl download <path>` to force a re-download, or right-click the file in Finder → "Download Now". Until they're materialized, bootstrap/hash will skip them.
- **Vault path resolution returns the wrong file** → check `settings.vault_files_dir` (in `app/config.py`) and the AudioFile's `identifier` + `file_type` columns. The canonical resolver is `resolve_audio_path` in `backend/app/services/vault.py`. Vault paths are `{vault_files_dir}/{identifier}.{ext}` — flat, no nesting. If `identifier` is NULL the resolver falls back to legacy `file_path`, which is the legacy path and often the source of confusion.
- **`Address already in use` / EADDRINUSE on :8000 or :5175** → a stale process from a previous run. Fix: `pkill -f "uvicorn app.main:app"` and `pkill -f "vite.*5175"`, then re-run `dev.sh`.
- **Vite shows blank page, no console errors** → almost always the stale optimized-deps cache. Same fix as the 504 case above.

## Rules

- **Read-only by default.** This skill diagnoses; the user authorizes fixes. The one exception: tailing logs and curling local ports — those are observation, not mutation.
- **Don't restart servers blindly.** If the backend is down, find out why from the log *before* suggesting a restart. A restart that masks a syntax error wastes everyone's time.
- **Don't edit code** as part of diagnosis. If a code fix is needed (e.g. a CORS port), surface it as a suggestion and wait for explicit approval — that's a separate task with its own PR / commit, per `docs/CONTRIBUTING.md`.
- If none of the known pitfalls match, say so explicitly: "Hot error doesn't match any known pitfall — full log tail attached, recommend manual review." Don't fabricate a fix.
