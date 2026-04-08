from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AudioFile, Song, Take
from app.schemas.audio_file import AudioFileRead
from app.schemas.song import SongDetail, SongRead, SongUpdate
from app.schemas.take import TakeRead

router = APIRouter(prefix="/api/repertoire", tags=["repertoire"])


def _song_to_read(song: Song, db: Session) -> SongRead:
    has_audio = db.query(AudioFile.id).filter(AudioFile.song_id == song.id).first() is not None
    take_count = db.query(func.count(Take.id)).filter(Take.song_id == song.id).scalar()
    return SongRead(
        id=song.id,
        title=song.title,
        artist=song.artist,
        project=song.project,
        is_original=song.is_original,
        status=song.status,
        times_practiced=song.times_practiced,
        notes=song.notes,
        created_at=song.created_at,
        updated_at=song.updated_at,
        has_audio=has_audio,
        take_count=take_count,
    )


@router.get("", response_model=list[SongRead])
def list_songs(
    project: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    is_original: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Song)
    if project:
        q = q.filter(Song.project == project)
    if status:
        q = q.filter(Song.status == status)
    if is_original is not None:
        q = q.filter(Song.is_original == is_original)
    if search:
        q = q.filter(Song.title.ilike(f"%{search}%"))

    songs = q.order_by(Song.times_practiced.desc(), Song.title).all()
    return [_song_to_read(s, db) for s in songs]


@router.get("/{song_id}", response_model=SongDetail)
def get_song(song_id: int, db: Session = Depends(get_db)):
    song = db.query(Song).get(song_id)
    if not song:
        raise HTTPException(404, "Song not found")

    takes = db.query(Take).filter(Take.song_id == song_id).all()
    audio_files = db.query(AudioFile).filter(AudioFile.song_id == song_id).all()

    take_reads = []
    for t in takes:
        tr = TakeRead.model_validate(t)
        if t.session:
            tr.session_date = str(t.session.date)
        take_reads.append(tr)

    base = _song_to_read(song, db)
    return SongDetail(
        **base.model_dump(),
        takes=take_reads,
        audio_files=[AudioFileRead.model_validate(a) for a in audio_files],
    )


@router.patch("/{song_id}", response_model=SongRead)
def update_song(song_id: int, data: SongUpdate, db: Session = Depends(get_db)):
    song = db.query(Song).get(song_id)
    if not song:
        raise HTTPException(404, "Song not found")

    if data.status is not None:
        song.status = data.status
    if data.notes is not None:
        song.notes = data.notes
    song.updated_at = datetime.now()

    db.commit()
    db.refresh(song)
    return _song_to_read(song, db)
