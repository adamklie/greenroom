"""File upload: saves imports into the vault as flat {identifier}.{ext} files.

Video files are kept as-is (the clip plays as video; audio extracts on demand),
matching the practice-clip convention. Uploads can be grouped into a session.
"""

import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import project_editor
from app.database import get_db
from app.models import AudioFile, PracticeSession, Song
from app.models.audio_file import generate_identifier
from app.services.vault import ingest_into_vault

router = APIRouter(prefix="/api/upload", tags=["upload"])

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}


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
    session_id: int | None = Form(None),
    recorded_at: str | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(project_editor),
):
    """Upload a file into the vault as {identifier}.{ext}.

    The file is buffered to a tempfile then copied into the vault as-is —
    video files keep their video (audio extracts on demand). Optionally links
    the recording to a song and/or groups it under a session.
    """
    if not file.filename:
        raise HTTPException(400, "No filename")

    # Validate the session up front (scoped — can't attach to another project's
    # session). recorded_at is the session date so clips sort by when they happened.
    session = None
    if session_id:
        session = db.query(PracticeSession).get(session_id)
        if not session:
            raise HTTPException(404, "Session not found")

    # Recorded date: an explicit value (YYYY-MM-DD) wins; otherwise a session
    # clip inherits the session date, and a plain import stays empty.
    if recorded_at:
        try:
            recorded = datetime.combine(date.fromisoformat(recorded_at), datetime.min.time())
        except ValueError:
            raise HTTPException(400, "recorded_at must be YYYY-MM-DD")
    elif session:
        recorded = datetime.combine(session.date, datetime.min.time())
    else:
        recorded = None

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

    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
        shutil.copyfileobj(file.file, tf)
        staged = Path(tf.name)

    try:
        ext = staged.suffix.lstrip(".").lower()
        is_video = staged.suffix.lower() in VIDEO_EXTENSIONS
        identifier = generate_identifier(file.filename)

        vault_dest = ingest_into_vault(staged, identifier, ext)

        af = AudioFile(
            song_id=song_id,
            file_path=vault_dest.name,  # just the vault filename; vault_dir is implied
            file_type=ext,
            identifier=identifier,
            submitted_file_name=Path(file.filename).name,  # strip any folder prefix (webkitdirectory)
            source=source,
            role=role,
            session_id=session_id,
            video_path=vault_dest.name if is_video else None,
            recorded_at=recorded,
            uploaded_at=datetime.now(),
        )
        db.add(af)
        db.commit()
        db.refresh(af)

        return {
            "ok": True,
            "audio_file_id": af.id,
            "song_id": song_id,
            "session_id": session_id,
            "identifier": identifier,
            "filename": vault_dest.name,
            "is_video": is_video,
        }
    finally:
        # Clean up the tempfile regardless of success — the vault has the copy.
        if staged.exists():
            try:
                staged.unlink()
            except OSError:
                pass
