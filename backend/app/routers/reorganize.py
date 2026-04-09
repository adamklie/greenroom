"""Reorganize API — preview and execute filesystem reorganization."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.reorganize import execute_reorganize, preview_reorganize

router = APIRouter(prefix="/api/reorganize", tags=["reorganize"])


@router.get("/preview")
def preview(db: Session = Depends(get_db)):
    """Preview what would change without moving anything."""
    result = preview_reorganize(db)
    return {
        "moves": [{
            "audio_file_id": m.audio_file_id,
            "song_id": m.song_id,
            "song_title": m.song_title,
            "song_artist": m.song_artist,
            "song_type": m.song_type,
            "current_path": m.current_path,
            "proposed_path": m.proposed_path,
            "reason": m.reason,
        } for m in result.moves],
        "already_organized": result.already_organized,
        "missing_files": result.missing_files,
        "unlinked_files": result.unlinked_files,
        "total_moves": len(result.moves),
    }


class ExecuteRequest(BaseModel):
    move_ids: list[int] | None = None  # None = move all


@router.post("/execute")
def execute(req: ExecuteRequest, db: Session = Depends(get_db)):
    """Execute the reorganization."""
    result = execute_reorganize(db, move_ids=req.move_ids)
    return {
        "moved": result.moved,
        "skipped": result.skipped,
        "errors": result.errors,
    }
