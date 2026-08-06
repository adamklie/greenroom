---
description: Upload folders of practice clips to prod Greenroom as sessions, then archive the sources to iCloud. Triggers on "get these sessions on greenroom", "ingest todo", "upload practice sessions", "new practice folders". Usage: /ingest-sessions
---

# /ingest-sessions

Takes dated folders of practice clips (typically staged in `todo/`) and gets them onto **prod** (`greenroom-1.fly.dev`) as sessions, then archives the source folders to iCloud.

**Not the same as [/ingest-recordings](../ingest-recordings/SKILL.md)**, which drives the *local* filesystem-scan path (`make bootstrap` → `hash` → `backup`) against the local vault. This skill is the *HTTP upload to prod* path. If the files are already in the vault and you want the DB to notice them, that's `/ingest-recordings`. If the files are loose on disk and need to get to prod, it's this one.

## The tool

`backend/scripts/repair_session_upload.py` — syncs one folder into one session.

It diffs the local folder against the session's existing clips **by `submitted_file_name` basename** and uploads only the gap. That dedupe is what makes it idempotent. The vault identifier is `sha256(filename + wall-clock)`, *not* content — so it would never collapse duplicates on its own. Re-running without the diff would create a second vault copy of every file. Never bypass the diff.

It produces rows identical to the Import page's grouped-session upload: `role=practice_clip`, `recorded_at` inherited from the session date server-side, clips left unlinked to songs.

## Instructions

### 1. Auth

Needs two cookies from a logged-in browser — DevTools → Application → Cookies on `greenroom-1.fly.dev`:

- `GR_COOKIE` ← `greenroom_session` (a JWT; expires, so it's usually stale from last time)
- `GR_PROJECT` ← `greenroom_project` (the active project id; stable, reusable)

These are **not** stored anywhere in the repo or shell rc. Ask the user to write them to a scratchpad file and source it — don't have them pasted into the transcript, and never echo the values.

### 2. Match the existing convention — do not assume

Before uploading anything, read what's already on prod. This doubles as the cheap auth check before pushing gigabytes.

```bash
# naming convention
curl -s -H "Cookie: greenroom_session=$GR_COOKIE" -H "X-Greenroom-Project: $GR_PROJECT" \
  https://greenroom-1.fly.dev/api/sessions | jq '.[] | {id,date,name}'

# field convention on a recent session
curl -s -H "Cookie: greenroom_session=$GR_COOKIE" -H "X-Greenroom-Project: $GR_PROJECT" \
  https://greenroom-1.fly.dev/api/sessions/<id> \
  | jq '[.audio_files[] | {source, role, linked: (.song_id != null)}] | group_by(.) | map({v:.[0], n:length})'
```

Report the inferred naming pattern and the `source` value in use, then **confirm with the user before uploading**. The script defaults `--source unknown` (the Import page's default), but the real options are `phone`, `logic_pro`, `garageband`, `suno_ai`, `collaborator`, `download`, `unknown`. If prod uses something else, pass `--source`.

Don't consult the local `greenroom.db` for this — it's stale (still `practice_sessions`, no `name` column). Prod is the source of truth.

### 3. Upload, one folder at a time, oldest first

Per folder, three commands. Never batch folders together.

```bash
# a. dry run — creates nothing, prints what it would do
python backend/scripts/repair_session_upload.py --dir todo/2026_06_27 \
  --date 2026-06-27 --create --name "<confirmed>"

# b. apply
#    ... same command + --apply    -> expect "Done: N uploaded, 0 failed"

# c. re-run the dry run
#    ... same as (a)               -> expect "Nothing to do — session already
#                                      contains every local file."
```

Step (c) is the proof every file landed, and it's also the resume path: if an upload dies partway, just re-run (b) — it backfills only the gap.

If any folder reports failures, **stop**. Don't start the next folder.

### 4. Convention check after the first folder only

Re-run the step-2 clip query against the newly created session and diff it against the reference session. `source`/`role` distribution must match. This catches a convention break after 28 files instead of after 98.

### 5. Archive to iCloud

Destination: `~/Library/Mobile Documents/com~apple~CloudDocs/music/Practice Sessions/`

This is a *different tree* from the vault (`CloudDocs/greenroom/`, `DEFAULT_VAULT_DIR` in `backend/app/config.py`). Nothing scans it, so archived originals won't be re-ingested as duplicates. That separation is load-bearing — don't archive into the vault.

macOS TCC blocks reads of iCloud paths under the default sandbox (`Operation not permitted`). A collision check that "passes" while sandboxed is meaningless — run it with the sandbox disabled and re-check for real.

Per folder, only once step 3(c) passed:
1. Check for a destination collision. If the folder exists with files in it, **stop and ask** — never merge.
2. `rsync -av --exclude='.DS_Store' todo/<date>/ "<dest>/<date>/"`
3. Verify file count and total bytes match the source.
4. Only then `rm -rf todo/<date>`.

## Rules

- **Never** delete a source folder before both the session re-check (3c) and the byte/count verify (5.3) have passed.
- **Never** merge into a colliding iCloud destination. Stop and ask.
- **Never** bypass the script's filename diff — the identifier is not content-addressed and will happily duplicate every file.
- **Don't** guess the session naming or `source`. Read it off prod and confirm.
- **Don't** echo cookie values into the transcript.
- One folder at a time; stop the pipeline on the first failure.
