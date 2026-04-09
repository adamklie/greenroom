"""File upload and import API — receive files from the browser and classify them."""

import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AudioFile, Song

router = APIRouter(prefix="/api/upload", tags=["upload"])

# Where uploaded files land before being organized
INBOX_DIR = "_inbox"

PROJECT_DIRS = {
    "solo": "Solo",
    "ozone_destructors": "Ozone Destructors/Recordings",
    "sural": "Sural",
    "joe": "Joe",
    "ideas": "Ideas",
}


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
    """Upload a file, optionally classify it, and add to the database.

    If song_id is provided, links to that song.
    If create_song_title is provided, creates a new song first.
    If neither, the file goes to the inbox for later triage.
    """
    if not file.filename:
        raise HTTPException(400, "No filename")

    # Determine destination directory
    if song_id or create_song_title:
        dest_subdir = PROJECT_DIRS.get(project, "_inbox")
    else:
        dest_subdir = INBOX_DIR

    dest_dir = settings.music_dir / dest_subdir
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Handle filename collisions
    dest_file = dest_dir / file.filename
    if dest_file.exists():
        stem = dest_file.stem
        suffix = dest_file.suffix
        counter = 1
        while dest_file.exists():
            dest_file = dest_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    # Save file
    with open(dest_file, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Create song if requested
    if create_song_title and not song_id:
        new_song = Song(
            title=create_song_title,
            type=song_type,
            project=project,
            status="idea",
            notes=notes,
        )
        db.add(new_song)
        db.flush()
        song_id = new_song.id

    # Create audio file record
    rel_path = str(dest_file.relative_to(settings.music_dir))
    ext = dest_file.suffix.lstrip(".").lower()

    af = AudioFile(
        song_id=song_id,
        file_path=rel_path,
        file_type=ext,
        source=source,
        role=role,
    )
    db.add(af)
    db.commit()
    db.refresh(af)

    return {
        "ok": True,
        "audio_file_id": af.id,
        "song_id": song_id,
        "file_path": rel_path,
        "filename": dest_file.name,
    }
