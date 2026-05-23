---
description: Start the greenroom backend + frontend dev servers and report health. Triggers on "start greenroom", "run greenroom", "spin up the app", "is the app running", "restart backend", "tail the logs". Usage: /run-greenroom
---

# /run-greenroom

Bring greenroom up locally via `dev.sh`, wait for both servers to bind, and surface health + last-40 log lines so the user can see immediately whether things are healthy.

## Instructions

Run the steps below in order. Do **not** skip steps — if a step fails, stop and report rather than proceeding.

### 1. Launch dev.sh

`dev.sh` is the canonical one-command start. It kills stale processes, clears the Vite optimized-deps cache, then starts the backend on :8000 and Vite on :5175. Logs land in `/tmp/greenroom-backend.log` and `/tmp/greenroom-frontend.log`.

```bash
bash ~/code/greenroom/dev.sh
```

`dev.sh` already polls both ports for up to 60s and prints health on its own. Capture and surface its stdout — don't re-implement what it does.

### 2. Confirm ports are bound

If `dev.sh` reports either port did not bind, poll once more to be sure (race conditions with iCloud-backed FS are real):

```bash
lsof -i:8000
lsof -i:5175
```

If a port is still not bound after `dev.sh` finished, jump to `/debug-servers` — do **not** restart blindly.

### 3. Hit /api/health

```bash
curl -s http://localhost:8000/api/health
```

Expected: `{"status": "ok", "app": "greenroom", "version": "0.2.0"}`. Surface the raw JSON to the user.

### 4. Tail the logs

Show the last 40 lines of each log so the user can see startup warnings / errors:

```bash
tail -n 40 /tmp/greenroom-backend.log
tail -n 40 /tmp/greenroom-frontend.log
```

### 5. Print the URL

End with a single line so the user can copy-paste:

```
→ http://localhost:5175
```

## Rules

- Never start servers on ports other than :8000 (backend) and :5175 (frontend) — those are the ports CORS in `backend/app/main.py` is configured for, and the ports `dev.sh` uses.
- Don't kill processes manually — `dev.sh` handles that. If `dev.sh` itself is wedged, use `/debug-servers` to diagnose first.
- Don't `--reload` the backend. iCloud filesystem semantics make `uvicorn --reload` flaky; `dev.sh` deliberately omits it.
- If `/api/health` returns non-200 or `curl` times out, surface the tail of `/tmp/greenroom-backend.log` and hand off to `/debug-servers` — don't try to "fix" the backend in this skill.
