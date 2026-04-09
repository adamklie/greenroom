from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PracticeSession, Tag, Take
from app.schemas.session import SessionDetail, SessionRead
from app.schemas.take import TakeRead, TakeUpdate

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _take_to_read(t: Take) -> TakeRead:
    tr = TakeRead.model_validate(t)
    tr.tags = [tg.name for tg in t.tags]
    if t.song:
        tr.song_title = t.song.title
    if t.session:
        tr.session_date = str(t.session.date)
    return tr


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
    sr = SessionRead.model_validate(session)
    sr.take_count = len(takes)
    return SessionDetail(**sr.model_dump(), takes=[_take_to_read(t) for t in takes])


@router.get("/takes/best", response_model=list[TakeRead])
def best_takes(
    min_rating: int = Query(1),
    song_id: int | None = Query(None),
    dimension: str = Query("overall"),
    db: Session = Depends(get_db),
):
    """Get highest-rated takes. Filter by dimension (overall, vocals, guitar, etc.)."""
    rating_col = getattr(Take, f"rating_{dimension}", Take.rating_overall)
    q = db.query(Take).filter(rating_col.isnot(None), rating_col >= min_rating)
    if song_id:
        q = q.filter(Take.song_id == song_id)
    takes = q.order_by(rating_col.desc()).limit(50).all()
    return [_take_to_read(t) for t in takes]


# --- Take CRUD ---

@router.patch("/takes/{take_id}", response_model=TakeRead)
def update_take(take_id: int, data: TakeUpdate, db: Session = Depends(get_db)):
    take = db.query(Take).get(take_id)
    if not take:
        raise HTTPException(404, "Take not found")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(take, field, value)
    db.commit()
    db.refresh(take)
    return _take_to_read(take)


@router.post("/takes/{take_id}/tags")
def add_take_tag(take_id: int, tag_name: str = Query(...), db: Session = Depends(get_db)):
    take = db.query(Take).get(take_id)
    if not take:
        raise HTTPException(404, "Take not found")
    tag = db.query(Tag).filter_by(name=tag_name).first()
    if not tag:
        tag = Tag(name=tag_name, category="take", is_predefined=False)
        db.add(tag)
        db.flush()
    if tag not in take.tags:
        take.tags.append(tag)
    db.commit()
    return {"ok": True, "tags": [t.name for t in take.tags]}


@router.delete("/takes/{take_id}/tags/{tag_name}")
def remove_take_tag(take_id: int, tag_name: str, db: Session = Depends(get_db)):
    take = db.query(Take).get(take_id)
    if not take:
        raise HTTPException(404, "Take not found")
    tag = db.query(Tag).filter_by(name=tag_name).first()
    if tag and tag in take.tags:
        take.tags.remove(tag)
    db.commit()
    return {"ok": True, "tags": [t.name for t in take.tags]}
