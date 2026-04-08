from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PracticeSession, Take
from app.schemas.session import SessionDetail, SessionRead
from app.schemas.take import TakeRead, TakeUpdate

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionRead])
def list_sessions(
    project: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(PracticeSession)
    if project:
        q = q.filter(PracticeSession.project == project)

    sessions = q.order_by(PracticeSession.date.desc()).all()
    result = []
    for s in sessions:
        take_count = db.query(func.count(Take.id)).filter(Take.session_id == s.id).scalar()
        sr = SessionRead.model_validate(s)
        sr.take_count = take_count
        result.append(sr)
    return result


@router.get("/{session_id}", response_model=SessionDetail)
def get_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(PracticeSession).get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")

    takes = db.query(Take).filter(Take.session_id == session_id).all()
    take_reads = []
    for t in takes:
        tr = TakeRead.model_validate(t)
        if t.song:
            tr.song_title = t.song.title
        tr.session_date = str(session.date)
        take_reads.append(tr)

    take_count = len(takes)
    sr = SessionRead.model_validate(session)
    sr.take_count = take_count
    return SessionDetail(**sr.model_dump(), takes=take_reads)


@router.patch("/takes/{take_id}", response_model=TakeRead)
def update_take(take_id: int, data: TakeUpdate, db: Session = Depends(get_db)):
    take = db.query(Take).get(take_id)
    if not take:
        raise HTTPException(404, "Take not found")

    if data.rating is not None:
        take.rating = data.rating
    if data.notes is not None:
        take.notes = data.notes

    db.commit()
    db.refresh(take)

    tr = TakeRead.model_validate(take)
    if take.song:
        tr.song_title = take.song.title
    if take.session:
        tr.session_date = str(take.session.date)
    return tr
