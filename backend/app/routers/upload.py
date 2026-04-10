"""File upload and import API — files go directly to organized locations."""

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AudioFile, Song
from app.services.autosync import compute_organized_path

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("")
async def upload_file(
    file: UploadFile = File(...),
    song_id: int | None = Form(None),
    create_song_title: str | None = Form(None),
    song_type: str = Form("idea"),
    project: str = Form("solo"),
    source: str = Form("unknown"),
    role: str = Form("recording"),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Upload a file directly to its organized location.

    Files are placed in Covers/, Originals/, or Ideas/ based on the
    song they're linked to. Unlinked files go to _inbox/.
    """
    if not file.filename:
        raise HTTPException(400, "No filename")

    # Create song if requested
    song = None
    if song_id:
        song = db.query(Song).get(song_id)
    elif create_song_title:
        song = Song(
            title=create_song_title,
            type=song_type,
            project=project,
            status="idea",
            notes=notes,
        )
        db.add(song)
        db.flush()
        song_id = song.id

    # Compute organized destination
    if song:
        target_rel = compute_organized_path(song, file.filename)
    else:
        target_rel = f"_inbox/{file.filename}"

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
        target_rel = str(target_full.relative_to(settings.music_dir))

    # Save file
    with open(target_full, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Create audio file record
    from datetime import datetime
    ext = target_full.suffix.lstrip(".").lower()
    af = AudioFile(
        song_id=song_id,
        file_path=target_rel,
        file_type=ext,
        source=source,
        role=role,
        uploaded_at=datetime.now(),
    )
    db.add(af)
    db.commit()
    db.refresh(af)

    return {
        "ok": True,
        "audio_file_id": af.id,
        "song_id": song_id,
        "file_path": target_rel,
        "filename": target_full.name,
    }
