from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Setlist, SetlistItem, Song
from app.schemas.setlist import (
    SetlistCreate,
    SetlistItemRead,
    SetlistRead,
    SetlistUpdate,
)

router = APIRouter(prefix="/api/setlists", tags=["setlists"])


def _setlist_to_read(setlist: Setlist, db: Session) -> SetlistRead:
    items = []
    for item in setlist.items:
        song = db.query(Song).get(item.song_id)
        items.append(SetlistItemRead(
            id=item.id,
            song_id=item.song_id,
            position=item.position,
            duration_minutes=item.duration_minutes,
            notes=item.notes,
            song_title=song.title if song else None,
            song_artist=song.artist if song else None,
            song_status=song.status if song else None,
        ))

    total = sum(i.duration_minutes for i in items)
    return SetlistRead(
        id=setlist.id,
        name=setlist.name,
        description=setlist.description,
        config=setlist.config,
        created_at=setlist.created_at,
        updated_at=setlist.updated_at,
        items=items,
        total_minutes=total,
        song_count=len(items),
    )


@router.get("", response_model=list[SetlistRead])
def list_setlists(db: Session = Depends(get_db)):
    setlists = db.query(Setlist).order_by(Setlist.updated_at.desc()).all()
    return [_setlist_to_read(s, db) for s in setlists]


@router.post("", response_model=SetlistRead)
def create_setlist(data: SetlistCreate, db: Session = Depends(get_db)):
    setlist = Setlist(name=data.name, description=data.description, config=data.config)
    db.add(setlist)
    db.flush()

    for item_data in data.items:
        db.add(SetlistItem(
            setlist_id=setlist.id,
            song_id=item_data.song_id,
            position=item_data.position,
            duration_minutes=item_data.duration_minutes,
            notes=item_data.notes,
        ))

    db.commit()
    db.refresh(setlist)
    return _setlist_to_read(setlist, db)


@router.get("/{setlist_id}", response_model=SetlistRead)
def get_setlist(setlist_id: int, db: Session = Depends(get_db)):
    setlist = db.query(Setlist).get(setlist_id)
    if not setlist:
        raise HTTPException(404, "Setlist not found")
    return _setlist_to_read(setlist, db)


@router.patch("/{setlist_id}", response_model=SetlistRead)
def update_setlist(setlist_id: int, data: SetlistUpdate, db: Session = Depends(get_db)):
    setlist = db.query(Setlist).get(setlist_id)
    if not setlist:
        raise HTTPException(404, "Setlist not found")

    if data.name is not None:
        setlist.name = data.name
    if data.description is not None:
        setlist.description = data.description
    if data.config is not None:
        setlist.config = data.config

    if data.items is not None:
        # Replace all items
        db.query(SetlistItem).filter(SetlistItem.setlist_id == setlist_id).delete()
        for item_data in data.items:
            db.add(SetlistItem(
                setlist_id=setlist_id,
                song_id=item_data.song_id,
                position=item_data.position,
                duration_minutes=item_data.duration_minutes,
                notes=item_data.notes,
            ))

    setlist.updated_at = datetime.now()
    db.commit()
    db.refresh(setlist)
    return _setlist_to_read(setlist, db)


@router.delete("/{setlist_id}")
def delete_setlist(setlist_id: int, db: Session = Depends(get_db)):
    setlist = db.query(Setlist).get(setlist_id)
    if not setlist:
        raise HTTPException(404, "Setlist not found")
    db.delete(setlist)
    db.commit()
    return {"ok": True}
