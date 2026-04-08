import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AudioFile, Take

router = APIRouter(prefix="/api/media", tags=["media"])

MIME_MAP = {
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
}


def _get_mime(path: Path) -> str:
    return MIME_MAP.get(path.suffix.lower(), mimetypes.guess_type(str(path))[0] or "application/octet-stream")


def _resolve_and_serve(rel_path: str | None, kind: str) -> FileResponse:
    if not rel_path:
        raise HTTPException(404, f"No {kind} path available")
    full = settings.music_dir / rel_path
    if not full.exists():
        raise HTTPException(404, f"{kind.title()} file not found")
    return FileResponse(full, media_type=_get_mime(full))


@router.get("/take/{take_id}/audio")
def stream_take_audio(take_id: int, db: Session = Depends(get_db)):
    take = db.query(Take).get(take_id)
    if not take:
        raise HTTPException(404, "Take not found")
    return _resolve_and_serve(take.audio_path, "audio")


@router.get("/take/{take_id}/video")
def stream_take_video(take_id: int, db: Session = Depends(get_db)):
    take = db.query(Take).get(take_id)
    if not take:
        raise HTTPException(404, "Take not found")
    return _resolve_and_serve(take.video_path, "video")


@router.get("/audio/{audio_file_id}")
def stream_audio_file(audio_file_id: int, db: Session = Depends(get_db)):
    af = db.query(AudioFile).get(audio_file_id)
    if not af:
        raise HTTPException(404, "Audio file not found")
    return _resolve_and_serve(af.file_path, "audio")


@router.get("/file/{file_path:path}")
def stream_file(file_path: str):
    """Stream any file by relative path from music directory."""
    full = settings.music_dir / file_path
    # Security: ensure the resolved path is within music_dir
    try:
        full.resolve().relative_to(settings.music_dir.resolve())
    except ValueError:
        raise HTTPException(403, "Access denied")
    if not full.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(full, media_type=_get_mime(full))
