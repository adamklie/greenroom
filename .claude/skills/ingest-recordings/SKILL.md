---
description: Run the post-practice ingestion pipeline — bootstrap (filesystem scan) + hash (auto-heal) + backup (DB snapshot). Triggers on "I have new recordings", "ingest practice from <date>", "I just finished a session", "rescan files". Usage: /ingest-recordings
---

# /ingest-recordings

After a practice session, run the canonical three-step ingestion: filesystem scan → file hashing → DB backup. Each step has its own Makefile target — call them in order.

## Instructions

### 1. Confirm the music directory

```bash
echo "${GREENROOM_VAULT_DIR:-<not set; backend will use default from app.config.settings>}"
```

If `GREENROOM_VAULT_DIR` is unset, the backend's `settings.vault_dir` default is used. Don't try to override — surface what's about to be scanned and ask the user to confirm before continuing if anything looks wrong (e.g. iCloud placeholder files in the tree).

### 2. Bootstrap — scan filesystem into the DB

```bash
cd ~/code/greenroom && make bootstrap
```

This runs `python -m app.services.bootstrap` against the vault. It picks up new audio/video files, registers them as `AudioFile` rows, and links them to songs where the filename matches. Capture the stdout — `bootstrap` typically prints a summary including any new unlinked files. Surface that count to the user.

### 3. Hash — auto-heal file integrity

```bash
cd ~/code/greenroom && make hash
```

Equivalent to `from app.services.backup import hash_all_files`. Prints a summary like `Hashed: <N> new, <N> cached, <N> missing`. The `missing` count matters — those are DB rows whose files have vanished. If `missing > 0`, mention it but don't auto-fix; the user can run `backend/scripts/cleanup_orphan_audio_files.py --list-only` to inspect, then `--yes` (soft) or `--hard --yes` (permanent) to clean up.

### 4. Backup — snapshot the DB

```bash
cd ~/code/greenroom && make backup
```

Calls `backup_database()`, which writes a timestamped copy of `greenroom.db` to the backup location. Prints the path written. iCloud filesystems sometimes block briefly here — if you see `sqlite3.OperationalError: database is locked`, the auto-backup on app startup is probably still running. Wait 10s and retry; if it still fails, hand off to `/debug-servers`.

## JSON export (in-app now)

The previous `make export` target and `exports/annotations_latest.json` git-tracked snapshot are gone. To export annotations, use **Settings → Export JSON** in the running app (`http://localhost:5173` in dev, `https://greenroom-1.fly.dev` in prod). It hits `GET /api/backup/export-download` and streams a dated JSON file to your browser.

## Rules

- **Don't** skip steps. Bootstrap → hash → backup is the canonical order. Running them out of order works but the backup may capture a stale state.
- **Don't** `git add` audio/DB/vault files. The audio/video files live in the iCloud vault. The DB is in `.gitignore`.
- **Don't** auto-resolve "missing" files reported by `make hash`. Those need user attention. Surface the count, don't act.
- If any step exits non-zero, STOP — don't continue with downstream steps. The pipeline is sequential by design.
