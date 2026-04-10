"""Auto-sync: filesystem always mirrors database.

When song metadata changes, files move automatically.
When a file is imported, it goes directly to the right place.
When something is deleted, it's soft-deleted first.
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models import AudioFile, Song


def _safe_name(name: str) -> str:
    """Make a string safe for filesystem use."""
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name[:100]


def compute_organized_path(song: Song, filename: str) -> str:
    """Compute where a file should live based on song metadata.

    Returns a path relative to music_dir:
      Covers/{Artist} - {Title}/{filename}
      Originals/{Title}/{filename}        (or Originals/{Project} - {Title}/...)
      Ideas/{filename}
    """
    if song.type == "cover":
        artist = _safe_name(song.artist or "Unknown Artist")
        title = _safe_name(song.title)
        return f"Covers/{artist} - {title}/{filename}"

    elif song.type == "original":
        title = _safe_name(song.title)
        if song.project and song.project not in ("solo", "ideas"):
            project_name = _safe_name(song.project.replace("_", " ").title())
            return f"Originals/{project_name} - {title}/{filename}"
        return f"Originals/{title}/{filename}"

    elif song.type == "idea":
        return f"Ideas/{filename}"

    return f"_unsorted/{filename}"


def resolve_path(file_path: str) -> Path:
    """Resolve a file path to absolute."""
    p = Path(file_path)
    if p.is_absolute():
        return p
    return settings.music_dir / file_path


def sync_song_files(db: Session, song: Song) -> list[str]:
    """Move all audio files for a song to their correct location.

    Call this after any metadata change (type, project, title, artist).
    Returns list of moves performed.
    """
    moves = []

    for af in db.query(AudioFile).filter_by(song_id=song.id).all():
        if af.is_stem:
            continue

        current_full = resolve_path(af.file_path)
        if not current_full.exists():
            continue

        filename = current_full.name
        target_rel = compute_organized_path(song, filename)
        target_full = settings.music_dir / target_rel

        # Already in the right place?
        try:
            current_rel = str(current_full.relative_to(settings.music_dir))
        except ValueError:
            current_rel = af.file_path

        if current_rel == target_rel:
            continue

        # Move the file
        target_full.parent.mkdir(parents=True, exist_ok=True)

        # Handle collision
        if target_full.exists() and target_full != current_full:
            stem = target_full.stem
            suffix = target_full.suffix
            counter = 1
            while target_full.exists():
                target_full = target_full.parent / f"{stem}_{counter}{suffix}"
                target_rel = str(target_full.relative_to(settings.music_dir))
                counter += 1

        shutil.move(str(current_full), str(target_full))
        af.file_path = target_rel
        moves.append(f"{current_rel} → {target_rel}")

        # Clean up empty parent directory
        _cleanup_empty_parent(current_full.parent)

    db.flush()
    return moves


def place_imported_file(dest_path: Path, song: Song | None) -> str:
    """Determine where to save an imported file.

    Returns absolute path where the file should be saved.
    If song is provided, places in organized location.
    If not, places in _inbox/.
    """
    filename = dest_path.name

    if song:
        target_rel = compute_organized_path(song, filename)
    else:
        target_rel = f"_inbox/{filename}"

    target_full = settings.music_dir / target_rel
    target_full.parent.mkdir(parents=True, exist_ok=True)

    # Handle collision
    if target_full.exists():
        stem = target_full.stem
        suffix = target_full.suffix
        counter = 1
        while target_full.exists():
            target_full = target_full.parent / f"{stem}_{counter}{suffix}"
            counter += 1

    return str(target_full)


# --- Soft Delete ---

TRASH_DIR = "_trash"


def soft_delete_song(db: Session, song_id: int) -> dict:
    """Soft-delete a song: move files to _trash/, mark as deleted in DB."""
    song = db.query(Song).get(song_id)
    if not song:
        raise ValueError(f"Song {song_id} not found")

    trash_dir = settings.music_dir / TRASH_DIR
    trash_dir.mkdir(parents=True, exist_ok=True)

    files_trashed = 0
    for af in db.query(AudioFile).filter_by(song_id=song.id).all():
        current_full = resolve_path(af.file_path)
        if current_full.exists():
            trash_path = trash_dir / current_full.name
            # Handle collision in trash
            if trash_path.exists():
                stem = trash_path.stem
                suffix = trash_path.suffix
                counter = 1
                while trash_path.exists():
                    trash_path = trash_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            shutil.move(str(current_full), str(trash_path))
            af.file_path = str(trash_path.relative_to(settings.music_dir))
            files_trashed += 1

        # Clean up empty parent
        if current_full.parent.exists():
            _cleanup_empty_parent(current_full.parent)

    # Mark song as deleted with timestamp
    song.status = "deleted"
    song.notes = (song.notes or "") + f"\n[Deleted: {datetime.now().isoformat()}]"
    db.commit()

    return {"song_id": song_id, "title": song.title, "files_trashed": files_trashed}


def restore_song(db: Session, song_id: int) -> dict:
    """Restore a soft-deleted song: move files back, update status."""
    song = db.query(Song).get(song_id)
    if not song or song.status != "deleted":
        raise ValueError(f"Song {song_id} not found or not deleted")

    # Restore status to idea (user can reclassify)
    song.status = "idea"
    # Remove deletion note
    if song.notes:
        song.notes = re.sub(r'\n\[Deleted:.*?\]', '', song.notes).strip() or None

    # Move files back to organized location
    moves = sync_song_files(db, song)
    db.commit()

    return {"song_id": song_id, "title": song.title, "files_restored": len(moves)}


def purge_trash(db: Session, older_than_days: int = 30) -> dict:
    """Permanently delete files in _trash/ older than N days."""
    trash_dir = settings.music_dir / TRASH_DIR
    if not trash_dir.exists():
        return {"purged": 0}

    cutoff = datetime.now() - timedelta(days=older_than_days)
    purged = 0

    for f in trash_dir.iterdir():
        if not f.is_file():
            continue
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        if mtime < cutoff:
            # Remove from DB
            af = db.query(AudioFile).filter_by(
                file_path=str(f.relative_to(settings.music_dir))
            ).first()
            if af:
                db.delete(af)
            f.unlink()
            purged += 1

    # Also remove songs that have been deleted and have no audio files
    deleted_songs = db.query(Song).filter_by(status="deleted").all()
    songs_purged = 0
    for song in deleted_songs:
        remaining_files = db.query(AudioFile).filter_by(song_id=song.id).count()
        if remaining_files == 0:
            db.delete(song)
            songs_purged += 1

    db.commit()
    return {"files_purged": purged, "songs_purged": songs_purged}


def list_trash(db: Session) -> list[dict]:
    """List items in the trash."""
    trash_dir = settings.music_dir / TRASH_DIR
    if not trash_dir.exists():
        return []

    items = []
    for f in sorted(trash_dir.iterdir()):
        if not f.is_file():
            continue
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        days_until_purge = 30 - (datetime.now() - mtime).days
        items.append({
            "filename": f.name,
            "size_mb": round(f.stat().st_size / (1024 * 1024), 1),
            "deleted_at": mtime.isoformat(),
            "days_until_purge": max(0, days_until_purge),
        })
    return items


def _cleanup_empty_parent(dir_path: Path):
    """Remove a directory if it's empty, and its parent if also empty."""
    protected = {"greenroom", ".claude", "_audio_exports", "backups", "exports",
                 ".git", "Covers", "Originals", "Ideas", "_trash", "_inbox"}
    for _ in range(3):  # Walk up max 3 levels
        if not dir_path.exists() or not dir_path.is_dir():
            break
        if dir_path.name in protected:
            break
        if dir_path == settings.music_dir:
            break
        try:
            if not any(dir_path.iterdir()):
                dir_path.rmdir()
                dir_path = dir_path.parent
            else:
                break
        except OSError:
            break
