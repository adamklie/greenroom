import mimetypes
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
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
    ".MP4": "video/mp4",
}


def _get_mime(path: Path) -> str:
    return MIME_MAP.get(path.suffix, mimetypes.guess_type(str(path))[0] or "application/octet-stream")


def _resolve_path(file_path: str) -> Path:
    """Resolve a file path — handles both relative and absolute."""
    p = Path(file_path)
    if p.is_absolute():
        return p
    return settings.music_dir / file_path


def _serve_with_range(full_path: Path, request: Request) -> StreamingResponse | FileResponse:
    """Serve a file with Range header support for seeking."""
    if not full_path.exists():
        raise HTTPException(404, "File not found")

    file_size = full_path.stat().st_size
    mime = _get_mime(full_path)
    range_header = request.headers.get("range")

    if range_header:
        # Parse Range: bytes=START-END
        range_match = range_header.replace("bytes=", "").split("-")
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1
        end = min(end, file_size - 1)
        content_length = end - start + 1

        def iter_file():
            with open(full_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(8192, remaining)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        return StreamingResponse(
            iter_file(),
            status_code=206,
            media_type=mime,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Accept-Ranges": "bytes",
            },
        )

    # No Range header — serve full file
    return FileResponse(
        full_path,
        media_type=mime,
        headers={"Accept-Ranges": "bytes", "Content-Length": str(file_size)},
    )


def _resolve_and_serve(rel_path: str | None, kind: str, request: Request) -> StreamingResponse | FileResponse:
    if not rel_path:
        raise HTTPException(404, f"No {kind} path available")
    full = _resolve_path(rel_path)
    if not full.exists():
        raise HTTPException(404, f"{kind.title()} file not found")
    return _serve_with_range(full, request)


@router.get("/take/{take_id}/audio")
def stream_take_audio(take_id: int, request: Request, db: Session = Depends(get_db)):
    take = db.query(Take).get(take_id)
    if not take:
        raise HTTPException(404, "Take not found")
    return _resolve_and_serve(take.audio_path, "audio", request)


@router.get("/take/{take_id}/video")
def stream_take_video(take_id: int, request: Request, db: Session = Depends(get_db)):
    take = db.query(Take).get(take_id)
    if not take:
        raise HTTPException(404, "Take not found")
    return _resolve_and_serve(take.video_path, "video", request)


@router.get("/audio/{audio_file_id}")
def stream_audio_file(audio_file_id: int, request: Request, db: Session = Depends(get_db)):
    af = db.query(AudioFile).get(audio_file_id)
    if not af:
        raise HTTPException(404, "Audio file not found")
    return _resolve_and_serve(af.file_path, "audio", request)


@router.get("/file/{file_path:path}")
def stream_file(file_path: str, request: Request):
    """Stream any file by path. Supports absolute paths and relative to music_dir."""
    full = _resolve_path(file_path)

    # Security: for relative paths, ensure within music_dir
    if not Path(file_path).is_absolute():
        try:
            full.resolve().relative_to(settings.music_dir.resolve())
        except ValueError:
            raise HTTPException(403, "Access denied")

    return _serve_with_range(full, request)
