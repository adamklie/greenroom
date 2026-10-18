from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.auth.deps import project_editor, project_viewer
from app.database import get_db
from app.models import Setlist, SetlistItem, Song
from app.schemas.setlist import (
    SetlistCreate,
    SetlistImportResult,
    SetlistItemRead,
    SetlistRead,
    SetlistUpdate,
)
from app.services.setlist_import import SetlistImportError, import_setlist

router = APIRouter(prefix="/api/setlists", tags=["setlists"])


def _require_accessible_songs(items, db: Session) -> None:
    """Every setlist item must reference a song in the active project. A written
    FK isn't covered by the read filter, so check the requested ids against a
    scoped lookup (which only returns songs in scope) in a single query."""
    wanted = {i.song_id for i in items if i.song_id is not None}
    if not wanted:
        return
    found = {sid for (sid,) in db.query(Song.id).filter(Song.id.in_(wanted)).all()}
    if wanted - found:
        raise HTTPException(400, "Setlist references songs you can't access")


def _effective_links(song_links: list | None, item_links: list | None) -> list:
    """Song links, with every kind the item overrides replaced by the item's."""
    item_links = item_links or []
    overridden = {link["kind"] for link in item_links}
    return [link for link in (song_links or []) if link["kind"] not in overridden] + item_links


def _item_values(item_data) -> dict:
    return dict(
        song_id=item_data.song_id,
        position=item_data.position,
        duration_minutes=item_data.duration_minutes,
        notes=item_data.notes,
        section=item_data.section,
        links=[link.model_dump() for link in item_data.links] or None,
    )


def _setlist_to_read(setlist: Setlist, db: Session) -> SetlistRead:
    items = []
    for item in setlist.items:
        song = item.song
        items.append(SetlistItemRead(
            id=item.id,
            song_id=item.song_id,
            position=item.position,
            duration_minutes=item.duration_minutes,
            notes=item.notes,
            section=item.section,
            links=item.links or [],
            effective_links=_effective_links(song.links if song else None, item.links),
            song_title=song.title if song else None,
            song_artist=song.artist if song else None,
            song_status=song.status if song else None,
            song_key=song.key if song else None,
            song_tempo_bpm=song.tempo_bpm if song else None,
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
def list_setlists(db: Session = Depends(get_db), _user=Depends(project_viewer)):
    setlists = db.query(Setlist).order_by(Setlist.updated_at.desc()).all()
    return [_setlist_to_read(s, db) for s in setlists]


@router.post("", response_model=SetlistRead)
def create_setlist(data: SetlistCreate, db: Session = Depends(get_db), _user=Depends(project_editor)):
    _require_accessible_songs(data.items, db)
    setlist = Setlist(name=data.name, description=data.description, config=data.config)
    db.add(setlist)
    db.flush()

    for item_data in data.items:
        db.add(SetlistItem(setlist_id=setlist.id, **_item_values(item_data)))

    db.commit()
    db.refresh(setlist)
    return _setlist_to_read(setlist, db)


@router.post("/import", response_model=SetlistImportResult)
async def import_setlist_xlsx(
    file: UploadFile = File(...), db: Session = Depends(get_db), _user=Depends(project_editor)
):
    """Create a setlist (and any missing songs) from a set-list .xlsx sheet."""
    try:
        setlist, matched, created = import_setlist(db, await file.read())
    except SetlistImportError as e:
        raise HTTPException(400, str(e))
    return SetlistImportResult(
        setlist=_setlist_to_read(setlist, db), songs_matched=matched, songs_created=created
    )


@router.get("/{setlist_id}", response_model=SetlistRead)
def get_setlist(setlist_id: int, db: Session = Depends(get_db), _user=Depends(project_viewer)):
    setlist = db.query(Setlist).get(setlist_id)
    if not setlist:
        raise HTTPException(404, "Setlist not found")
    return _setlist_to_read(setlist, db)


@router.patch("/{setlist_id}", response_model=SetlistRead)
def update_setlist(setlist_id: int, data: SetlistUpdate, db: Session = Depends(get_db), _user=Depends(project_editor)):
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
        _require_accessible_songs(data.items, db)
        # Replace all items
        db.query(SetlistItem).filter(SetlistItem.setlist_id == setlist_id).delete()
        for item_data in data.items:
            db.add(SetlistItem(setlist_id=setlist_id, **_item_values(item_data)))

    setlist.updated_at = datetime.now()
    db.commit()
    db.refresh(setlist)
    return _setlist_to_read(setlist, db)


@router.delete("/{setlist_id}")
def delete_setlist(setlist_id: int, db: Session = Depends(get_db), _user=Depends(project_editor)):
    setlist = db.query(Setlist).get(setlist_id)
    if not setlist:
        raise HTTPException(404, "Setlist not found")
    db.delete(setlist)
    db.commit()
    return {"ok": True}
