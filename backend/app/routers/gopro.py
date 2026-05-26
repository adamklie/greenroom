"""GoPro session workflow API — analyze videos, process clips."""

import re
import shutil
import tempfile
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import require_editor, require_viewer
from app.config import settings
from app.database import get_db
from app.services.gopro_processor import (
    ClipMarker,
    analyze_video,
    list_video_files,
    process_session,
)
from app.services.vault import CLOUD_UNSUPPORTED_MESSAGE, get_backend, is_cloud_backend

router = APIRouter(prefix="/api/gopro", tags=["gopro"])


def _sanitize_filename(name: str) -> str:
    """Strip path components and replace risky chars. Mirrors upload.py's
    intent (we want a safe leaf name for the R2 key)."""
    leaf = Path(name).name  # drop any path components
    # Collapse whitespace to underscores, drop anything that isn't a sane
    # filename character. Keep dots so the extension survives.
    cleaned = re.sub(r"\s+", "_", leaf.strip())
    cleaned = re.sub(r"[^A-Za-z0-9._\-]", "", cleaned)
    return cleaned or "video.mp4"


class AnalyzeRequest(BaseModel):
    video_path: str
    drop_db: float = 6.0        # dB below median to count as a gap
    min_gap_duration: float = 2.0
    min_clip_duration: float = 30.0
    window_seconds: float = 3.0


class ClipInput(BaseModel):
    start_seconds: float
    end_seconds: float
    clip_name: str
    song_id: int | None = None


class ProcessRequest(BaseModel):
    source_path: str
    session_date: str
    project: str = "ozone_destructors"
    clips: list[ClipInput]
    existing_session_id: int | None = None


@router.get("/list-videos")
def get_video_list(directory: str, _user=Depends(require_viewer)):
    """List video files in a local directory. Not meaningful in cloud mode —
    the Fly machine has no GoPro source library mounted."""
    if is_cloud_backend():
        raise HTTPException(status_code=501, detail=CLOUD_UNSUPPORTED_MESSAGE)
    files = list_video_files(directory)
    return {"files": files, "directory": directory}


@router.post("/analyze")
def analyze(req: AnalyzeRequest, _user=Depends(require_editor)):
    """Analyze video using energy-based gap detection.

    Requires local file access + ffmpeg. Not supported in cloud mode.
    TODO: enable in cloud mode after audio extraction — would require
    downloading the raw R2 object to /tmp first.
    """
    if is_cloud_backend():
        raise HTTPException(status_code=501, detail=CLOUD_UNSUPPORTED_MESSAGE)
    try:
        result = analyze_video(
            req.video_path,
            drop_db=req.drop_db,
            min_gap_duration=req.min_gap_duration,
            min_clip_duration=req.min_clip_duration,
            window_seconds=req.window_seconds,
        )
        return {
            "video_path": result.video_path,
            "duration_seconds": result.duration_seconds,
            "median_db": result.median_db,
            "threshold_db": result.threshold_db,
            "proposed_clips": [
                {
                    "start_seconds": c.start_seconds,
                    "end_seconds": c.end_seconds,
                    "duration_seconds": c.duration_seconds,
                    "suggested_name": c.suggested_name,
                }
                for c in result.proposed_clips
            ],
            "energy_profile": [
                {"time": p.time, "db": p.db}
                for p in result.energy_profile
            ],
        }
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {e}")


@router.post("/process")
def process(req: ProcessRequest, db: Session = Depends(get_db), _user=Depends(require_editor)):
    """Process marked clips.

    Local mode: `source_path` is a filesystem path to the raw video. ffmpeg
    slices into the session folder, DB rows reference relative paths.

    Cloud mode: `source_path` is an R2 object key (e.g. `raw/20260525T2200_video.mp4`)
    returned by `/api/gopro/upload-raw`. The raw object is downloaded to a
    tempdir, sliced with ffmpeg, then each cut is uploaded to R2 at
    `files/{identifier}.mp4`. Request stays open while ffmpeg runs (no job
    queue) — expect 3-5 min for a typical GoPro practice video.
    """
    try:
        session_date = date.fromisoformat(req.session_date)
    except ValueError:
        raise HTTPException(400, f"Invalid date: {req.session_date}")

    if is_cloud_backend():
        # In cloud mode, source_path is the R2 key (e.g. "raw/...mp4"). The
        # processor downloads it before slicing, so we don't validate
        # existence here — let it bubble up as a clean error.
        source_key = req.source_path
        source_video_name = Path(source_key).name
        source_directory = source_key  # passed through to the cloud branch
    else:
        source_file = Path(req.source_path)
        if not source_file.exists():
            raise HTTPException(400, f"Video not found: {req.source_path}")
        source_video_name = source_file.name
        source_directory = str(source_file.parent)

    clips = [
        ClipMarker(
            source_video=source_video_name,
            start_seconds=c.start_seconds,
            end_seconds=c.end_seconds,
            clip_name=c.clip_name,
            song_id=c.song_id,
        )
        for c in req.clips
    ]

    try:
        result = process_session(
            db=db, source_directory=source_directory,
            session_date=session_date, clips=clips, project=req.project,
            existing_session_id=req.existing_session_id,
        )
        return {
            "session_id": result.session_id,
            "session_date": result.session_date,
            "clips_processed": result.clips_processed,
            "audio_extracted": result.audio_extracted,
            "errors": result.errors,
            "cuts_txt_path": result.cuts_txt_path,
        }
    except Exception as e:
        raise HTTPException(500, f"Processing failed: {e}")


@router.post("/upload-raw")
async def upload_raw(
    file: UploadFile = File(...),
    _user=Depends(require_editor),
):
    """Stream a raw GoPro video into storage and return a handle.

    Cloud mode: writes to R2 at `raw/{timestamp}_{safe-filename}` and
    returns the R2 key. The frontend passes this key back as `source_path`
    when calling `/api/gopro/process`.

    Local mode: writes to `settings.vault_dir/raw/{safe-filename}` and
    returns the absolute filesystem path (which `/api/gopro/process` can
    consume directly).

    Also returns a presigned GET URL (cloud) or a `/api/media/file/...`
    URL (local) the browser can use as `<video src=>` for cut-marking
    playback. Presigned URLs are 1-hour TTL by default; if your processing
    workflow takes longer, request a fresh presign before submitting.
    """
    if not file.filename:
        raise HTTPException(400, "No filename")

    safe_name = _sanitize_filename(file.filename)

    # Buffer upload to a tempfile so the (potentially multi-GB) body never
    # sits in memory. Same pattern as upload.py.
    suffix = Path(safe_name).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
        shutil.copyfileobj(file.file, tf)
        staged = Path(tf.name)

    try:
        size_bytes = staged.stat().st_size

        if is_cloud_backend():
            backend = get_backend()
            s3 = backend._s3  # type: ignore[attr-defined]
            bucket = backend._bucket  # type: ignore[attr-defined]
            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            r2_key = f"raw/{timestamp}_{safe_name}"
            try:
                s3.upload_file(str(staged), bucket, r2_key)
            except Exception as e:
                raise HTTPException(500, f"R2 upload failed: {e}")

            # Presigned GET URL so the frontend can show the video for
            # cut-marking without going through the FastAPI process.
            try:
                playback_url = s3.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket, "Key": r2_key},
                    ExpiresIn=settings.r2_presign_ttl_seconds,
                )
            except Exception:
                playback_url = None

            return {
                "ok": True,
                "source_path": r2_key,
                "r2_key": r2_key,
                "size_bytes": size_bytes,
                "playback_url": playback_url,
                "filename": safe_name,
            }

        # Local mode: persist into vault_dir/raw/ so the Process flow has a
        # stable place to read from. The legacy "browse for path" flow still
        # works for users who'd rather point at /Volumes/GOPRO directly.
        raw_dir = settings.vault_dir / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        dest = raw_dir / safe_name
        # If a file with the same name already exists, prefix with timestamp
        # to avoid clobbering.
        if dest.exists():
            timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
            dest = raw_dir / f"{timestamp}_{safe_name}"
        shutil.copy2(staged, dest)

        return {
            "ok": True,
            "source_path": str(dest),
            "r2_key": None,
            "size_bytes": size_bytes,
            # The /api/media/file/ endpoint serves arbitrary filesystem paths
            # in local mode; encode so the browser can fetch it.
            "playback_url": f"/api/media/file/{dest}",
            "filename": safe_name,
        }
    finally:
        try:
            staged.unlink()
        except OSError:
            pass
