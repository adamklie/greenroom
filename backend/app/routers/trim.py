"""Audio trimming — extract a time range from an audio file into a new file."""

import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AudioFile
from app.models.audio_file import generate_identifier
from app.schemas.audio_file import AudioFileRead
from app.services.autosync import resolve_path

router = APIRouter(prefix="/api/audio-files", tags=["trim"])

FFMPEG = "/Users/adamklie/opt/ffmpeg"
if not Path(FFMPEG).exists():
    FFMPEG = "ffmpeg"


class TrimRequest(BaseModel):
    start_time: float
    end_time: float


@router.post("/{audio_file_id}/trim", response_model=AudioFileRead)
def trim_audio_file(audio_file_id: int, req: TrimRequest, db: Session = Depends(get_db)):
    """Trim an audio file to a time range, creating a new AudioFile."""
    af = db.query(AudioFile).get(audio_file_id)
    if not af:
        raise HTTPException(404, "Audio file not found")

    source_path = resolve_path(af.file_path)
    if not source_path.exists():
        raise HTTPException(404, f"Source file not found on disk: {af.file_path}")

    if req.start_time >= req.end_time:
        raise HTTPException(400, "start_time must be less than end_time")

    # Generate output filename
    stem = source_path.stem
    ext = source_path.suffix
    start_label = f"{req.start_time:.1f}".replace(".", "_")
    end_label = f"{req.end_time:.1f}".replace(".", "_")
    out_name = f"{stem}_trim_{start_label}s_{end_label}s{ext}"
    out_path = source_path.parent / out_name

    # Handle collision
    if out_path.exists():
        counter = 1
        while out_path.exists():
            out_name = f"{stem}_trim_{start_label}s_{end_label}s_{counter}{ext}"
            out_path = source_path.parent / out_name
            counter += 1

    # Run ffmpeg
    cmd = [
        FFMPEG, "-i", str(source_path),
        "-ss", str(req.start_time),
        "-to", str(req.end_time),
        "-c", "copy",
        "-y", str(out_path),
    ]
    try:
        subprocess.run(cmd, capture_output=True, timeout=120, check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(500, f"ffmpeg failed: {e.stderr.decode()[:500]}")
    except FileNotFoundError:
        raise HTTPException(500, "ffmpeg not found")

    if not out_path.exists():
        raise HTTPException(500, "Trim produced no output file")

    # Compute relative path
    try:
        rel_path = str(out_path.relative_to(settings.music_dir))
    except ValueError:
        rel_path = str(out_path)

    # Create new AudioFile record
    new_af = AudioFile(
        song_id=af.song_id,
        file_path=rel_path,
        file_type=ext.lstrip(".").lower(),
        identifier=generate_identifier(out_name),
        submitted_file_name=out_name,
        source=af.source,
        role=af.role,
        notes=f"Trimmed from {af.identifier or f'id:{af.id}'} ({req.start_time}s - {req.end_time}s)",
        uploaded_at=datetime.now(),
    )
    db.add(new_af)
    db.commit()
    db.refresh(new_af)

    return AudioFileRead.model_validate(new_af)
