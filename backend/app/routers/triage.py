from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AudioFile, Song, TriageItem
from app.schemas.triage import TriageClassify, TriageItemRead

router = APIRouter(prefix="/api/triage", tags=["triage"])


@router.get("", response_model=list[TriageItemRead])
def list_triage(
    status: str = Query("pending"),
    db: Session = Depends(get_db),
):
    q = db.query(TriageItem)
    if status:
        q = q.filter(TriageItem.status == status)
    return q.order_by(TriageItem.discovered_at.desc()).all()


@router.patch("/{item_id}", response_model=TriageItemRead)
def classify_triage_item(item_id: int, data: TriageClassify, db: Session = Depends(get_db)):
    item = db.query(TriageItem).get(item_id)
    if not item:
        raise HTTPException(404, "Triage item not found")

    # Determine the song to link to
    song_id = data.song_id
    if not song_id and data.create_song_title:
        new_song = Song(
            title=data.create_song_title,
            type=data.song_type,
            project="solo",
            status="idea",
        )
        db.add(new_song)
        db.flush()
        song_id = new_song.id

    # Update the audio file record if it exists
    af = db.query(AudioFile).filter_by(file_path=item.file_path).first()
    if af:
        af.song_id = song_id
        af.source = data.source
        af.role = data.role

    item.status = "classified"
    item.suggested_song_id = song_id
    item.suggested_type = data.song_type
    item.suggested_source = data.source

    db.commit()
    db.refresh(item)
    return item


@router.post("/{item_id}/skip", response_model=TriageItemRead)
def skip_triage_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(TriageItem).get(item_id)
    if not item:
        raise HTTPException(404, "Triage item not found")
    item.status = "skipped"
    db.commit()
    db.refresh(item)
    return item
