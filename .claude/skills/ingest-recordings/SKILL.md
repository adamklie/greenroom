---
description: Run the post-practice ingestion pipeline — bootstrap (filesystem scan), hash (auto-heal), export (annotations JSON), backup (DB snapshot). Triggers on "I have new recordings", "ingest practice from <date>", "I just finished a session", "rescan files". Usage: /ingest-recordings
---

# /ingest-recordings

After a practice session, run the canonical four-step ingestion: filesystem scan → file hashing → annotation export → DB backup. Each step has its own Makefile target — call them in order.

## Instructions

### 1. Confirm the music directory

```bash
echo "${GREENROOM_MUSIC_DIR:-<not set; backend will use default from app.config.settings>}"
```

If `GREENROOM_MUSIC_DIR` is unset, the backend's `settings.music_dir` default is used. Don't try to override — surface what's about to be scanned and ask the user to confirm before continuing if anything looks wrong (e.g. iCloud placeholder files in the tree).

### 2. Bootstrap — scan filesystem into the DB

```bash
cd ~/code/greenroom && make bootstrap
```

This runs `python -m app.services.bootstrap` against the music dir. It picks up new audio/video files, registers them as `AudioFile` rows, and links them to songs where the filename matches. Capture the stdout — `bootstrap` typically prints a summary including any new unlinked files. Surface that count to the user.

### 3. Hash — auto-heal file integrity

```bash
cd ~/code/greenroom && make hash
```

Equivalent to `from app.services.backup import hash_all_files`. Prints a summary like `Hashed: <N> new, <N> cached, <N> missing`. The `missing` count matters — those are DB rows whose files have vanished. If `missing > 0`, mention it but don't auto-fix; that's for the user to triage.

### 4. Export — write annotations to git-tracked JSON

```bash
cd ~/code/greenroom && make export
```

Writes `exports/annotations_latest.json` with the current state of all songs + takes. This is the recovery path described in `docs/ARCHITECTURE.md` (storage section) — if the DB ever gets corrupted, the JSON + vault files are enough to rebuild.

### 5. Backup — snapshot the DB

```bash
cd ~/code/greenroom && make backup
```

Calls `backup_database()`, which writes a timestamped copy of `greenroom.db` to the backup location. Prints the path written. iCloud filesystems sometimes block briefly here — if you see `sqlite3.OperationalError: database is locked`, the auto-backup on app startup is probably still running. Wait 10s and retry; if it still fails, hand off to `/debug-servers`.

### 6. Offer to commit the export

`exports/annotations_latest.json` is git-tracked because it's the canonical metadata snapshot. After the four steps above, ASK the user before committing — don't commit silently:

> "Want me to commit `exports/annotations_latest.json` so the latest snapshot lands in git?"

If yes:

```bash
cd ~/code/greenroom && git diff --stat exports/annotations_latest.json
# Show the user the diff size, then:
git add exports/annotations_latest.json
git commit -m "data: export annotations after <date> practice session"
```

If the user declines, leave the file dirty in the working tree — they can commit later as part of another PR.

## Rules

- **Don't** skip steps. Bootstrap → hash → export → backup is the canonical order in `Makefile` (and in `scripts/after-practice.sh`, which is what the `after-practice` make target invokes). Running them out of order works but the export may capture a stale state.
- **Don't** `git add` other files (DB, audio, vault). Only `exports/annotations_latest.json` is meant to be tracked. The audio/video files live in the iCloud vault — see `docs/ARCHITECTURE.md`.
- **Don't** auto-resolve "missing" files reported by `make hash`. Those need user attention (the file may have moved, been renamed, or been deleted). Surface the count, don't act.
- If any step exits non-zero, STOP — don't continue with downstream steps. The pipeline is sequential by design.
- `make after-practice` exists and runs roughly the same sequence via `scripts/after-practice.sh`. Use the individual targets in this skill so each step is observable; fall back to `make after-practice` if the user explicitly wants the all-in-one script.
