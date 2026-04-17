"""File upload: saves imports into the vault as flat {identifier}.{ext} files.

Video files are automatically stripped to audio (m4a) on upload.
"""

import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AudioFile, Song
from app.models.audio_file import generate_identifier
from app.services.vault import ingest_into_vault

router = APIRouter(prefix="/api/upload", tags=["upload"])

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
FFMPEG = "/Users/adamklie/opt/ffmpeg"
if not Path(FFMPEG).exists():
    FFMPEG = "ffmpeg"


def _extract_audio(video_path: Path) -> Path | None:
    """Extract audio from a video file to m4a. Returns path to audio file or None."""
    audio_path = video_path.with_suffix(".m4a")
    try:
        subprocess.run(
            [FFMPEG, "-i", str(video_path), "-vn", "-acodec", "aac", "-b:a", "192k", "-y", str(audio_path)],
            capture_output=True, timeout=120, check=True,
        )
        return audio_path
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return None


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
    """Upload a file into the vault.

    The incoming file is buffered to a tempfile, optionally transcoded
    (video → m4a), then copied into the vault as {identifier}.{ext}.
    The source the browser sent is not retained after the vault copy
    is made.
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

    # Buffer upload to a tempfile so ffmpeg (if needed) can read from disk.
    suffix = Path(file.filename).suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
        shutil.copyfileobj(file.file, tf)
        staged = Path(tf.name)

    try:
        is_video = staged.suffix.lower() in VIDEO_EXTENSIONS
        extracted_audio = False
        final_staged = staged

        if is_video:
            extracted = _extract_audio(staged)
            if extracted and extracted.exists():
                final_staged = extracted
                extracted_audio = True

        ext = final_staged.suffix.lstrip(".").lower()
        identifier = generate_identifier(file.filename)

        vault_dest = ingest_into_vault(final_staged, identifier, ext)

        af = AudioFile(
            song_id=song_id,
            file_path=vault_dest.name,  # just the vault filename; vault_dir is implied
            file_type=ext,
            identifier=identifier,
            submitted_file_name=file.filename,
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
            "identifier": identifier,
            "filename": vault_dest.name,
            "extracted_audio": extracted_audio,
            "original_format": staged.suffix if is_video else None,
        }
    finally:
        # Clean up tempfiles regardless of success. The vault already has a
        # copy; the staged upload never belonged on disk long-term.
        for p in {staged, final_staged}:
            if p.exists():
                try:
                    p.unlink()
                except OSError:
                    pass
