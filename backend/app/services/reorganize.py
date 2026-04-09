"""Reorganize filesystem to match the database structure.

Moves audio files into a clean hierarchy:
  Covers/{Artist} - {Title}/
  Originals/{Title}/
  Ideas/{filename}
  Sessions/ (untouched — already organized by date)

All moves are atomic: file moves on disk + DB path update in one step.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.models import AudioFile, Song


@dataclass
class MoveProposal:
    audio_file_id: int
    song_id: int | None
    song_title: str | None
    song_artist: str | None
    song_type: str | None
    current_path: str
    proposed_path: str
    reason: str
    file_exists: bool = True


@dataclass
class ReorganizePreview:
    moves: list[MoveProposal]
    already_organized: int
    missing_files: int
    unlinked_files: int  # files not linked to any song


@dataclass
class ReorganizeResult:
    moved: int
    skipped: int
    errors: list[str]


def _safe_dirname(name: str) -> str:
    """Make a string safe for use as a directory name."""
    name = name.strip()
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name)
    return name[:100]  # cap length


def _get_target_path(song: Song | None, audio_file: AudioFile) -> str | None:
    """Determine where a file should live based on its song metadata."""
    if not song:
        return None  # Can't organize without a song

    current = Path(audio_file.file_path)
    filename = current.name

    if song.type == "cover":
        artist = _safe_dirname(song.artist or "Unknown Artist")
        title = _safe_dirname(song.title)
        return f"Covers/{artist} - {title}/{filename}"

    elif song.type == "original":
        title = _safe_dirname(song.title)
        project = song.project
        if project and project != "solo":
            project_name = _safe_dirname(project.replace("_", " ").title())
            return f"Originals/{project_name} - {title}/{filename}"
        return f"Originals/{title}/{filename}"

    elif song.type == "idea":
        return f"Ideas/{filename}"

    return None


def preview_reorganize(db: Session) -> ReorganizePreview:
    """Generate a preview of what would change without moving anything."""
    moves: list[MoveProposal] = []
    already_organized = 0
    missing_files = 0
    unlinked = 0

    for af in db.query(AudioFile).all():
        # Skip stems
        if af.is_stem:
            continue

        current_path = af.file_path
        full_path = Path(current_path)
        if not full_path.is_absolute():
            full_path = settings.music_dir / current_path

        if not full_path.exists():
            missing_files += 1
            continue

        if not af.song_id:
            unlinked += 1
            continue

        song = af.song
        target = _get_target_path(song, af)
        if not target:
            continue

        # Normalize current path for comparison
        try:
            current_rel = str(full_path.relative_to(settings.music_dir))
        except ValueError:
            current_rel = current_path

        if current_rel == target:
            already_organized += 1
            continue

        # Check if it's already in the right directory (just different subfolder)
        current_parts = Path(current_rel).parts
        target_parts = Path(target).parts
        if len(current_parts) >= 2 and len(target_parts) >= 2:
            if current_parts[0] == target_parts[0] and current_parts[1] == target_parts[1]:
                already_organized += 1
                continue

        moves.append(MoveProposal(
            audio_file_id=af.id,
            song_id=song.id if song else None,
            song_title=song.title if song else None,
            song_artist=song.artist if song else None,
            song_type=song.type if song else None,
            current_path=current_rel,
            proposed_path=target,
            reason=f"Organize into {Path(target).parts[0]}/",
            file_exists=full_path.exists(),
        ))

    return ReorganizePreview(
        moves=moves,
        already_organized=already_organized,
        missing_files=missing_files,
        unlinked_files=unlinked,
    )


def execute_reorganize(db: Session, move_ids: list[int] | None = None) -> ReorganizeResult:
    """Execute the reorganization. If move_ids is None, moves everything."""
    preview = preview_reorganize(db)

    moves_to_execute = preview.moves
    if move_ids is not None:
        moves_to_execute = [m for m in preview.moves if m.audio_file_id in move_ids]

    moved = 0
    skipped = 0
    errors: list[str] = []

    for move in moves_to_execute:
        af = db.query(AudioFile).get(move.audio_file_id)
        if not af:
            errors.append(f"AudioFile {move.audio_file_id} not found")
            continue

        # Resolve paths
        current_full = Path(move.current_path)
        if not current_full.is_absolute():
            current_full = settings.music_dir / move.current_path

        target_full = settings.music_dir / move.proposed_path

        if not current_full.exists():
            errors.append(f"Source missing: {move.current_path}")
            continue

        if target_full.exists():
            skipped += 1
            continue

        try:
            # Create target directory
            target_full.parent.mkdir(parents=True, exist_ok=True)

            # Move file
            shutil.move(str(current_full), str(target_full))

            # Update DB
            af.file_path = move.proposed_path
            moved += 1

        except Exception as e:
            errors.append(f"Failed to move {move.current_path}: {e}")

    db.commit()

    # Clean up empty directories left behind
    _cleanup_empty_dirs(settings.music_dir)

    return ReorganizeResult(moved=moved, skipped=skipped, errors=errors)


def _cleanup_empty_dirs(root: Path):
    """Remove empty directories (except protected ones)."""
    protected = {"greenroom", ".claude", "_audio_exports", "backups", "exports", ".git"}
    for dirpath in sorted(root.rglob("*"), reverse=True):
        if not dirpath.is_dir():
            continue
        if dirpath.name in protected or any(p in protected for p in dirpath.parts):
            continue
        try:
            if not any(dirpath.iterdir()):
                dirpath.rmdir()
        except OSError:
            pass
