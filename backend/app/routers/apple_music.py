from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.apple_music import (
    get_cover_suggestions,
    get_listening_stats,
    import_listening_history,
)

router = APIRouter(prefix="/api/apple-music", tags=["apple-music"])


@router.post("/import")
def run_import(db: Session = Depends(get_db)):
    """Import listening history from Apple Music app."""
    try:
        stats = import_listening_history(db)
        return stats
    except RuntimeError as e:
        raise HTTPException(500, str(e))


@router.get("/stats")
def listening_stats(db: Session = Depends(get_db)):
    """Get aggregate listening statistics."""
    return get_listening_stats(db)


@router.get("/suggestions")
def cover_suggestions(limit: int = 20, db: Session = Depends(get_db)):
    """Get cover suggestions based on listening history."""
    return get_cover_suggestions(db, limit=limit)
