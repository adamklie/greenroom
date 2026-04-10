"""Trash management API — view, restore, and purge soft-deleted items."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Song
from app.services.autosync import list_trash, purge_trash, restore_song

router = APIRouter(prefix="/api/trash", tags=["trash"])


@router.get("")
def get_trash(db: Session = Depends(get_db)):
    """List items in the trash + deleted songs."""
    files = list_trash(db)
    deleted_songs = db.query(Song).filter_by(status="deleted").all()
    return {
        "files": files,
        "deleted_songs": [{
            "id": s.id,
            "title": s.title,
            "type": s.type,
            "project": s.project,
        } for s in deleted_songs],
    }


@router.post("/restore/{song_id}")
def restore(song_id: int, db: Session = Depends(get_db)):
    """Restore a soft-deleted song."""
    try:
        result = restore_song(db, song_id)
        return {"ok": True, **result}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/purge")
def purge(older_than_days: int = Query(30), db: Session = Depends(get_db)):
    """Permanently delete trashed files older than N days."""
    result = purge_trash(db, older_than_days=older_than_days)
    return {"ok": True, **result}
