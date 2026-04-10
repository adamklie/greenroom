"""Audio Files API — the fundamental unit. List, edit, and manage all recordings."""

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AudioFile, Song
from app.schemas.audio_file import AudioFileRead, AudioFileUpdate
from app.services.autosync import compute_organized_path, resolve_path, _cleanup_empty_parent

router = APIRouter(prefix="/api/audio-files", tags=["audio-files"])


def _af_to_read(af: AudioFile) -> AudioFileRead:
    """Convert AudioFile model to read schema with joined song info."""
    return AudioFileRead(
        id=af.id,
        song_id=af.song_id,
        file_path=af.file_path,
        file_type=af.file_type,
        source=af.source,
        role=af.role,
        version=af.version,
        rating_overall=af.rating_overall,
        rating_vocals=af.rating_vocals,
        rating_guitar=af.rating_guitar,
        rating_drums=af.rating_drums,
        rating_tone=af.rating_tone,
        rating_timing=af.rating_timing,
        rating_energy=af.rating_energy,
        notes=af.notes,
        created_at=af.created_at,
        song_title=af.song.title if af.song else None,
        song_artist=af.song.artist if af.song else None,
        song_type=af.song.type if af.song else None,
    )


@router.get("", response_model=list[AudioFileRead])
def list_audio_files(
    song_id: int | None = Query(None),
    source: str | None = Query(None),
    role: str | None = Query(None),
    has_song: bool | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """List all audio files with optional filters."""
    q = db.query(AudioFile).filter(AudioFile.is_stem == False)  # noqa: E712

    if song_id is not None:
        q = q.filter(AudioFile.song_id == song_id)
    if source:
        q = q.filter(AudioFile.source == source)
    if role:
        q = q.filter(AudioFile.role == role)
    if has_song is True:
        q = q.filter(AudioFile.song_id.isnot(None))
    elif has_song is False:
        q = q.filter(AudioFile.song_id.is_(None))
    if search:
        q = q.filter(AudioFile.file_path.ilike(f"%{search}%"))

    files = q.order_by(AudioFile.created_at.desc()).all()
    return [_af_to_read(af) for af in files]


@router.get("/{audio_file_id}", response_model=AudioFileRead)
def get_audio_file(audio_file_id: int, db: Session = Depends(get_db)):
    af = db.query(AudioFile).get(audio_file_id)
    if not af:
        raise HTTPException(404, "Audio file not found")
    return _af_to_read(af)


@router.patch("/{audio_file_id}", response_model=AudioFileRead)
def update_audio_file(audio_file_id: int, data: AudioFileUpdate, db: Session = Depends(get_db)):
    """Update audio file metadata. If song_id changes, file auto-moves."""
    af = db.query(AudioFile).get(audio_file_id)
    if not af:
        raise HTTPException(404, "Audio file not found")

    changes = data.model_dump(exclude_unset=True)
    song_changed = "song_id" in changes and changes["song_id"] != af.song_id

    for field, value in changes.items():
        setattr(af, field, value)

    db.commit()
    db.refresh(af)

    # Auto-move if song assignment changed
    if song_changed:
        _auto_move_file(af, db)

    return _af_to_read(af)


def _auto_move_file(af: AudioFile, db: Session):
    """Move file to match its song's organized location."""
    current_full = resolve_path(af.file_path)
    if not current_full.exists():
        return

    if af.song_id:
        song = db.query(Song).get(af.song_id)
        if song:
            target_rel = compute_organized_path(song, current_full.name)
        else:
            return
    else:
        target_rel = f"_inbox/{current_full.name}"

    target_full = settings.music_dir / target_rel

    try:
        current_rel = str(current_full.relative_to(settings.music_dir))
    except ValueError:
        current_rel = af.file_path

    if current_rel == target_rel:
        return

    target_full.parent.mkdir(parents=True, exist_ok=True)
    if not target_full.exists():
        shutil.move(str(current_full), str(target_full))
        af.file_path = target_rel
        db.commit()
        _cleanup_empty_parent(current_full.parent)
