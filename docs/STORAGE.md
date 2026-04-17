# Storage & Backup Strategy

Last updated: 2026-04-09

## Overview

Your music data has two layers with very different backup needs:

| Layer | Size | Changes | Value | Backup Strategy |
|-------|------|---------|-------|----------------|
| **Annotations** (ratings, lyrics, tags, notes, setlists) | ~1 MB | Frequently | Irreplaceable | Git-tracked JSON + DB auto-backup |
| **Audio/video files** | 20-200 GB | Rarely (once created) | Replaceable from source | iCloud Drive sync |

## What's Protected

### Annotations (Git-tracked)
- `exports/annotations_latest.json` — all songs, ratings, lyrics, tags, setlists
- Updated via `make export` or the Dashboard "Export JSON" button
- Git-tracked so every version is in your commit history
- **This is the most important file.** If you lost everything else, you could rebuild from this.

### Database (Auto-backup)
- `greenroom.db` backed up to `backups/` on every app startup
- Last 10 backups kept (timestamped)
- Manual backup: `make backup` or Dashboard "Backup DB" button
- Restore: Dashboard or `POST /api/backup/restore/{filename}`

### File Integrity (Content hashing)
- Every audio file gets a SHA256 fingerprint stored in the DB
- If a file is moved/renamed, "Check & Heal" finds it by content hash
- Run `make hash` after adding new files, or Dashboard "Hash Files"

## Audio/Video File Storage

### Current: Local Filesystem
```
~/Desktop/music/           ← 20GB, all music files
~/Desktop/music/greenroom/ ← App code + database + exports
```

### Recommended: iCloud Drive ($2.99/month for 200GB)

**Migration steps:**
1. Open System Settings → Apple Account → iCloud → iCloud Drive → turn ON
2. Upgrade to 200GB plan if needed ($2.99/month)
3. Move your music folder into iCloud Drive:
   ```bash
   mv ~/Desktop/music ~/Library/Mobile\ Documents/com~apple~CloudDocs/music
   ln -s ~/Library/Mobile\ Documents/com~apple~CloudDocs/music ~/Desktop/music
   ```
4. Update Greenroom config if needed (the symlink should make this transparent)

**What this gives you:**
- All files automatically synced to iCloud
- Accessible from your iPhone (listen to recordings on the go)
- 30-day version history on all files (Apple handles this)
- If your Mac dies, everything is in the cloud

**Important:** The symlink (`ln -s`) means `~/Desktop/music` still works — the app doesn't need any config changes.

### Alternative: Backblaze B2 (~$1/month)
If you prefer cheaper storage or want a second backup:
```bash
# Install b2 CLI
pip install b2

# Create bucket (one-time)
b2 authorize-account YOUR_KEY_ID YOUR_APP_KEY
b2 create-bucket greenroom-music allPrivate

# Sync (run periodically or via cron)
b2 sync ~/Desktop/music b2://greenroom-music
```

## Routine Maintenance

### After every practice session:
1. Process GoPro videos in the app
2. Rate your takes
3. `make export` to update the git-tracked JSON

### Weekly:
1. `git add exports/ && git commit -m "weekly annotation export"` 
2. `git push`

### Monthly:
1. `make hash` to fingerprint any new files
2. Check Dashboard "Data Protection" card for broken links
3. Verify iCloud sync is current (System Settings → iCloud → check storage)

## Disaster Recovery

### Scenario: Accidentally deleted a file
1. Check iCloud Drive "Recently Deleted" (30-day window)
2. Or: Dashboard → "Check & Heal" to find it if moved

### Scenario: Database corrupted
1. Dashboard → Backup → Restore from latest backup
2. Or: Copy from `backups/greenroom_YYYYMMDD_HHMMSS.db` → `greenroom.db`

### Scenario: Lost everything (new Mac)
1. Sign into iCloud → files sync back
2. Clone git repo → `make setup`
3. Import `exports/annotations_latest.json` (TODO: build import from JSON)
4. `make bootstrap` to re-scan filesystem
5. All annotations restored, all files present

### Scenario: File was moved, app shows broken link
1. Dashboard → "Hash Files" (if not already hashed)
2. Dashboard → "Check & Heal" → auto-fixes paths using content hash
3. If still broken: the file was deleted, check iCloud Recently Deleted

## What's NOT Backed Up (and shouldn't be)
- `node_modules/` — reinstall with `npm install`
- `__pycache__/` — regenerated automatically
- `greenroom.db` in git — too large, changes too often (use exports instead)
- `.venv/` — recreate with `pip install`

---

<!-- PENDING MERGE from VISION.md 2026-04-16 — integrate during STORAGE.md review -->

## File Storage (from VISION.md)

- **Primary:** Local filesystem (`~/Desktop/music/`)
- **Backup:** Cloud (TBD — iCloud, GCS, or Backblaze)
- **Future:** Cloud-primary for multi-device access
- **Paths:** Relative to music_dir in database, portable across machines
