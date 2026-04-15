"""GoPro session workflow API — analyze videos, process clips."""

from datetime import date
from pathlib import Path

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
def get_video_list(directory: str):
    files = list_video_files(directory)
    return {"files": files, "directory": directory}


@router.post("/analyze")
def analyze(req: AnalyzeRequest):
    """Analyze video using energy-based gap detection."""
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
def process(req: ProcessRequest, db: Session = Depends(get_db)):
    """Process marked clips."""
    try:
        session_date = date.fromisoformat(req.session_date)
    except ValueError:
        raise HTTPException(400, f"Invalid date: {req.session_date}")

    source_file = Path(req.source_path)
    if not source_file.exists():
        raise HTTPException(400, f"Video not found: {req.source_path}")

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
            db=db, source_directory=str(source_file.parent),
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
