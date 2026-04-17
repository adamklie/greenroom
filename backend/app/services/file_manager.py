"""File management: move, rename, consolidate, health check.

All file operations update the database atomically so links never break.
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models import AudioFile, Take
from app.services.vault import resolve_audio_path


@dataclass
class BrokenLink:
    table: str  # 'audio_files' or 'takes'
    record_id: int
    field: str  # 'file_path', 'audio_path', 'video_path'
    path: str
    song_title: str | None = None


@dataclass
class ConsolidateResult:
    moved: int
    skipped: int
    errors: list[str]


def resolve_path(file_path: str) -> Path:
    """Resolve a file path — handles both relative (to music_dir) and absolute."""
    p = Path(file_path)
    if p.is_absolute():
        return p
    return settings.music_dir / file_path


def health_check(db: Session) -> list[BrokenLink]:
    """Find all database records pointing to files that don't exist on disk."""
    broken: list[BrokenLink] = []

    # Check audio_files (vault-first: resolve_audio_path prefers the vault
    # path by identifier, falls back to legacy file_path)
    for af in db.query(AudioFile).all():
        full = resolve_audio_path(af)
        if not full.exists():
            song_title = af.song.title if af.song else None
            broken.append(BrokenLink(
                table="audio_files", record_id=af.id,
                field="file_path", path=af.file_path,
                song_title=song_title,
            ))

    # Check takes — audio_path and video_path
    for take in db.query(Take).all():
        if take.audio_path:
            full = resolve_path(take.audio_path)
            if not full.exists():
                song_title = take.song.title if take.song else None
                broken.append(BrokenLink(
                    table="takes", record_id=take.id,
                    field="audio_path", path=take.audio_path,
                    song_title=song_title,
                ))
        if take.video_path:
            full = resolve_path(take.video_path)
            if not full.exists():
                song_title = take.song.title if take.song else None
                broken.append(BrokenLink(
                    table="takes", record_id=take.id,
                    field="video_path", path=take.video_path,
                    song_title=song_title,
                ))

    return broken


def move_audio_file(db: Session, audio_file_id: int, new_path: str) -> AudioFile:
    """Move an audio file on disk and update the DB record atomically."""
    af = db.query(AudioFile).get(audio_file_id)
    if not af:
        raise ValueError(f"AudioFile {audio_file_id} not found")

    old_full = resolve_path(af.file_path)
    new_full = resolve_path(new_path)

    if not old_full.exists():
        raise FileNotFoundError(f"Source file not found: {old_full}")

    # Create destination directory if needed
    new_full.parent.mkdir(parents=True, exist_ok=True)

    # Move the file
    shutil.move(str(old_full), str(new_full))

    # Update DB
    af.file_path = new_path
    db.commit()
    db.refresh(af)
    return af


def move_take_audio(db: Session, take_id: int, new_audio_path: str) -> Take:
    """Move a take's audio file and update the DB."""
    take = db.query(Take).get(take_id)
    if not take or not take.audio_path:
        raise ValueError(f"Take {take_id} not found or has no audio")

    old_full = resolve_path(take.audio_path)
    new_full = resolve_path(new_audio_path)

    if not old_full.exists():
        raise FileNotFoundError(f"Source file not found: {old_full}")

    new_full.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(old_full), str(new_full))

    take.audio_path = new_audio_path
    db.commit()
    db.refresh(take)
    return take


def consolidate_file(db: Session, audio_file_id: int) -> str:
    """Move a file from an external location into the organized music directory.

    Files are placed based on their song's project:
      - solo → Solo/
      - ozone_destructors → Ozone Destructors/Recordings/
      - sural → Sural/
      - joe → Joe/
      - ideas → Ideas/
      - No song → _unsorted/
    """
    af = db.query(AudioFile).get(audio_file_id)
    if not af:
        raise ValueError(f"AudioFile {audio_file_id} not found")

    old_full = resolve_path(af.file_path)
    if not old_full.exists():
        raise FileNotFoundError(f"File not found: {old_full}")

    # Already inside music_dir?
    try:
        old_full.resolve().relative_to(settings.music_dir.resolve())
        # Check if it's actually in a proper subdirectory (not root or Desktop)
        rel = str(old_full.resolve().relative_to(settings.music_dir.resolve()))
        if "/" in rel:  # Has a subdirectory — already organized
            return af.file_path
    except ValueError:
        pass  # Outside music_dir, needs consolidation

    # Determine destination based on song project
    project_dirs = {
        "solo": "Solo",
        "ozone_destructors": "Ozone Destructors/Recordings",
        "sural": "Sural",
        "joe": "Joe",
        "ideas": "Ideas",
    }

    if af.song:
        dest_dir = project_dirs.get(af.song.project, "_unsorted")
    else:
        dest_dir = "_unsorted"

    dest_folder = settings.music_dir / dest_dir
    dest_folder.mkdir(parents=True, exist_ok=True)

    # Use original filename
    dest_file = dest_folder / old_full.name

    # Handle name collisions
    if dest_file.exists():
        stem = dest_file.stem
        suffix = dest_file.suffix
        counter = 1
        while dest_file.exists():
            dest_file = dest_folder / f"{stem}_{counter}{suffix}"
            counter += 1

    # COPY, not move — original stays where it is until user deletes it
    shutil.copy2(str(old_full), str(dest_file))

    # Update DB to point to the new copy inside Greenroom
    new_rel = str(dest_file.relative_to(settings.music_dir))
    af.file_path = new_rel
    db.commit()

    return new_rel


def consolidate_all_external(db: Session) -> ConsolidateResult:
    """Move all files outside the music directory into it."""
    moved = 0
    skipped = 0
    errors: list[str] = []

    for af in db.query(AudioFile).all():
        full = resolve_path(af.file_path)

        # Skip if already inside music_dir
        try:
            full.resolve().relative_to(settings.music_dir.resolve())
            skipped += 1
            continue
        except ValueError:
            pass

        if not full.exists():
            errors.append(f"Missing: {af.file_path}")
            continue

        try:
            consolidate_file(db, af.id)
            moved += 1
        except Exception as e:
            errors.append(f"Error moving {af.file_path}: {e}")

    return ConsolidateResult(moved=moved, skipped=skipped, errors=errors)


def file_hash(path: Path, chunk_size: int = 8192) -> str:
    """Compute SHA256 hash of a file (for future content-addressed storage)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            h.update(chunk)
    return h.hexdigest()
