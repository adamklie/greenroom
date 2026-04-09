"""GoPro session workflow API — analyze videos, process clips."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.gopro_processor import (
    ClipMarker,
    analyze_video,
    list_video_files,
    process_session,
)

router = APIRouter(prefix="/api/gopro", tags=["gopro"])


class AnalyzeRequest(BaseModel):
    video_path: str
    silence_threshold_db: int = -30
    min_silence_duration: float = 3.0
    min_clip_duration: float = 30.0


class ClipInput(BaseModel):
    start_seconds: float
    end_seconds: float
    clip_name: str
    song_id: int | None = None


class ProcessRequest(BaseModel):
    source_path: str
    session_date: str  # YYYY-MM-DD
    project: str = "ozone_destructors"
    clips: list[ClipInput]


@router.get("/list-videos")
def get_video_list(directory: str):
    """List video files in a directory (SD card, Desktop, etc.)."""
    files = list_video_files(directory)
    if not files:
        return {"files": [], "message": f"No video files found in {directory}"}
    return {"files": files, "directory": directory}


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    """Analyze a video file for silence gaps and propose clip boundaries."""
    try:
        result = analyze_video(
            req.video_path,
            silence_threshold_db=req.silence_threshold_db,
            min_silence_duration=req.min_silence_duration,
            min_clip_duration=req.min_clip_duration,
        )
        return {
            "video_path": result.video_path,
            "duration_seconds": result.duration_seconds,
            "proposed_clips": [
                {
                    "start_seconds": c.start_seconds,
                    "end_seconds": c.end_seconds,
                    "duration_seconds": c.duration_seconds,
                    "suggested_name": c.suggested_name,
                }
                for c in result.proposed_clips
            ],
            "silence_gaps": [
                {"start": s, "end": e} for s, e in result.silence_gaps
            ],
        }
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {e}")


@router.post("/process")
def process(req: ProcessRequest, db: Session = Depends(get_db)):
    """Process marked clips: cut video, extract audio, create DB records."""
    try:
        session_date = date.fromisoformat(req.session_date)
    except ValueError:
        raise HTTPException(400, f"Invalid date format: {req.session_date}")

    source_dir = str(type(None))  # Will use source_path's parent directory
    from pathlib import Path
    source_file = Path(req.source_path)
    if not source_file.exists():
        raise HTTPException(400, f"Source video not found: {req.source_path}")

    clips = [
        ClipMarker(
            source_video=source_file.name,
            start_seconds=c.start_seconds,
            end_seconds=c.end_seconds,
            clip_name=c.clip_name,
            song_id=c.song_id,
        )
        for c in req.clips
    ]

    try:
        result = process_session(
            db=db,
            source_directory=str(source_file.parent),
            session_date=session_date,
            clips=clips,
            project=req.project,
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
