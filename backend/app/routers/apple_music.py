from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.apple_music import (
    DEFAULT_EXCLUDED_GENRES,
    get_cover_suggestions,
    get_listening_stats,
)

router = APIRouter(prefix="/api/apple-music", tags=["apple-music"])


class IngestRequest(BaseModel):
    path: str  # path to Apple_Media_Services.zip or extracted dir
    wipe: bool = False


@router.post("/ingest-dump")
def ingest_dump(req: IngestRequest, db: Session = Depends(get_db)):
    """Ingest an Apple Media Services data-export zip or directory.

    Set wipe=true to clear existing listening data first.
    """
    from scripts.ingest_apple_dump import ingest

    src = Path(req.path)
    if not src.exists():
        raise HTTPException(400, f"Path not found: {req.path}")
    try:
        return ingest(db, src, wipe=req.wipe)
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/stats")
def listening_stats(
    include_all_genres: bool = Query(False),
    db: Session = Depends(get_db),
):
    exclude = set() if include_all_genres else DEFAULT_EXCLUDED_GENRES
    return get_listening_stats(db, exclude_genres=exclude)


@router.post("/link-songs")
def relink_songs(db: Session = Depends(get_db)):
    """Link listening_history rows to catalog songs by title/artist."""
    from scripts.link_listening_to_songs import link
    return link(db)


@router.get("/suggestions")
def cover_suggestions(
    limit: int = 20,
    include_all_genres: bool = Query(False),
    db: Session = Depends(get_db),
):
    exclude = set() if include_all_genres else DEFAULT_EXCLUDED_GENRES
    return get_cover_suggestions(db, limit=limit, exclude_genres=exclude)
