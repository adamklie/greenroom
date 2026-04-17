"""Data protection: auto-backup, content hashing, auto-heal, export.

The most important data in Greenroom is the annotations — ratings, tags,
lyrics, notes, song metadata. The audio files can be re-scanned from disk,
but the annotations can't be reconstructed. This module protects them.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AudioFile, ContentPost, PracticeSession, Setlist, SetlistItem, Song, Tag, Take
from app.services.file_manager import resolve_path


MAX_BACKUPS = 10  # Keep last N database backups


def _backup_dir() -> Path:
    """Vault-backed backup directory, created on demand."""
    settings.ensure_vault_layout()
    return settings.vault_backups_dir


# --- Database Backup ---

def backup_database() -> str:
    """Create a timestamped backup of greenroom.db. Returns backup path."""
    backup_dir = _backup_dir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"greenroom_{timestamp}.db"

    shutil.copy2(settings.db_path, backup_path)

    # Prune old backups
    backups = sorted(backup_dir.glob("greenroom_*.db"), reverse=True)
    for old in backups[MAX_BACKUPS:]:
        old.unlink()

    return str(backup_path)


def list_backups() -> list[dict]:
    """List available database backups."""
    backup_dir = settings.vault_backups_dir
    if not backup_dir.exists():
        return []
    backups = sorted(backup_dir.glob("greenroom_*.db"), reverse=True)
    return [{
        "filename": b.name,
        "path": str(b),
        "size_mb": round(b.stat().st_size / (1024 * 1024), 2),
        "created": datetime.fromtimestamp(b.stat().st_mtime).isoformat(),
    } for b in backups]


def restore_backup(backup_filename: str) -> str:
    """Restore a database backup. Creates a backup of current state first."""
    backup_path = settings.vault_backups_dir / backup_filename
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_filename}")

    # Safety: backup current state before restoring
    backup_database()

    shutil.copy2(backup_path, settings.db_path)
    return str(backup_path)


# --- Content Hashing ---

def compute_file_hash(file_path: str, chunk_size: int = 8192) -> str | None:
    """Compute SHA256 hash of a file."""
    full = resolve_path(file_path)
    if not full.exists():
        return None
    h = hashlib.sha256()
    with open(full, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()


def hash_all_files(db: Session) -> dict:
    """Compute and store SHA256 hashes for all audio files. Returns stats."""
    # We store hashes in the notes field of AudioFile for now
    # (adding a proper column would require migration)
    # Format: hash stored as "sha256:HEXDIGEST" prefix in a dedicated query
    from sqlalchemy import text

    # Check if content_hash column exists, add it if not
    try:
        db.execute(text("SELECT content_hash FROM audio_files LIMIT 1"))
    except Exception:
        db.rollback()
        db.execute(text("ALTER TABLE audio_files ADD COLUMN content_hash TEXT"))
        db.commit()

    total = 0
    hashed = 0
    skipped = 0
    missing = 0

    for af in db.query(AudioFile).all():
        total += 1

        # Check if already hashed
        existing_hash = db.execute(
            text("SELECT content_hash FROM audio_files WHERE id = :id"),
            {"id": af.id},
        ).scalar()

        if existing_hash:
            skipped += 1
            continue

        file_hash = compute_file_hash(af.file_path)
        if file_hash:
            db.execute(
                text("UPDATE audio_files SET content_hash = :hash WHERE id = :id"),
                {"hash": file_hash, "id": af.id},
            )
            hashed += 1
        else:
            missing += 1

    db.commit()
    return {"total": total, "newly_hashed": hashed, "already_hashed": skipped, "missing_files": missing}


# --- Auto-Heal ---

def auto_heal_paths(db: Session) -> dict:
    """Find broken file paths and try to fix them using content hashes.

    For each broken path:
    1. Look up the content_hash
    2. Scan the music directory for a file with matching hash
    3. If found, update the path
    """
    from sqlalchemy import text

    healed = 0
    unresolvable = 0
    checked = 0

    # Get all audio files with hashes
    rows = db.execute(
        text("SELECT id, file_path, content_hash FROM audio_files WHERE content_hash IS NOT NULL")
    ).fetchall()

    # Build a hash → new_path lookup by scanning filesystem
    hash_cache: dict[str, str] = {}

    for af_id, file_path, content_hash in rows:
        full = resolve_path(file_path)
        if full.exists():
            continue  # Path is fine

        checked += 1

        # Check cache first
        if content_hash in hash_cache:
            new_path = hash_cache[content_hash]
            db.execute(
                text("UPDATE audio_files SET file_path = :path WHERE id = :id"),
                {"path": new_path, "id": af_id},
            )
            healed += 1
            continue

        # Scan music directory for matching file
        found = _find_file_by_hash(content_hash, settings.music_dir)
        if found:
            try:
                new_rel = str(found.relative_to(settings.music_dir))
            except ValueError:
                new_rel = str(found)
            hash_cache[content_hash] = new_rel
            db.execute(
                text("UPDATE audio_files SET file_path = :path WHERE id = :id"),
                {"path": new_rel, "id": af_id},
            )
            healed += 1
        else:
            unresolvable += 1

    db.commit()
    return {"checked": checked, "healed": healed, "unresolvable": unresolvable}


def _find_file_by_hash(target_hash: str, search_dir: Path) -> Path | None:
    """Scan a directory tree for a file matching the given hash."""
    AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".aac", ".flac", ".mp4", ".mov"}
    for f in search_dir.rglob("*"):
        if not f.is_file() or f.suffix.lower() not in AUDIO_EXTS:
            continue
        if "greenroom" in str(f) and "backups" in str(f):
            continue
        h = hashlib.sha256()
        try:
            with open(f, "rb") as fh:
                while chunk := fh.read(8192):
                    h.update(chunk)
            if h.hexdigest() == target_hash:
                return f
        except (PermissionError, OSError):
            continue
    return None


# --- JSON Export ---

def export_annotations(db: Session) -> dict:
    """Export all annotations as a JSON-serializable dict.

    This captures everything that can't be reconstructed from the filesystem:
    ratings, tags, lyrics, notes, structured fields, setlists, content plans.
    """
    songs_data = []
    for song in db.query(Song).all():
        songs_data.append({
            "id": song.id,
            "title": song.title,
            "artist": song.artist,
            "type": song.type,
            "status": song.status,
            "project": song.project,
            "key": song.key,
            "tempo_bpm": song.tempo_bpm,
            "tuning": song.tuning,
            "vibe": song.vibe,
            "lyrics": song.lyrics,
            "notes": song.notes,
            "times_practiced": song.times_practiced,
            "tags": [t.name for t in song.tags],
        })

    takes_data = []
    for take in db.query(Take).all():
        takes_data.append({
            "id": take.id,
            "clip_name": take.clip_name,
            "song_id": take.song_id,
            "session_id": take.session_id,
            "rating_overall": take.rating_overall,
            "rating_vocals": take.rating_vocals,
            "rating_guitar": take.rating_guitar,
            "rating_drums": take.rating_drums,
            "rating_tone": take.rating_tone,
            "rating_timing": take.rating_timing,
            "rating_energy": take.rating_energy,
            "notes": take.notes,
            "tags": [t.name for t in take.tags],
        })

    setlists_data = []
    for sl in db.query(Setlist).all():
        items = db.query(SetlistItem).filter_by(setlist_id=sl.id).order_by(SetlistItem.position).all()
        setlists_data.append({
            "name": sl.name,
            "config": sl.config,
            "description": sl.description,
            "items": [{"song_id": i.song_id, "position": i.position,
                       "duration_minutes": i.duration_minutes, "notes": i.notes} for i in items],
        })

    content_data = []
    for post in db.query(ContentPost).all():
        content_data.append({
            "title": post.title,
            "song_id": post.song_id,
            "platform": post.platform,
            "scheduled_date": str(post.scheduled_date) if post.scheduled_date else None,
            "status": post.status,
            "caption": post.caption,
            "notes": post.notes,
        })

    export = {
        "exported_at": datetime.now().isoformat(),
        "songs": songs_data,
        "takes": takes_data,
        "setlists": setlists_data,
        "content_posts": content_data,
        "tags": [{"name": t.name, "category": t.category} for t in db.query(Tag).all()],
    }

    # Also save a timestamped copy into the vault exports dir. The sync router
    # additionally writes `annotations_latest.json` for the canonical pointer.
    settings.ensure_vault_layout()
    export_dir = settings.vault_exports_dir
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = export_dir / f"annotations_{timestamp}.json"
    export_path.write_text(json.dumps(export, indent=2))

    return {"path": str(export_path), "data": export}
