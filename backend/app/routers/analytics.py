"""Analytics API — practice progress, rating trends, skill radar."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PracticeSession, Song, Take

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

RATING_DIMS = ["overall", "vocals", "guitar", "drums", "tone", "timing", "energy"]


@router.get("/practice-frequency")
def practice_frequency(db: Session = Depends(get_db)):
    """Practice sessions per week/month for heatmap-style chart."""
    sessions = (
        db.query(PracticeSession.date, func.count(Take.id).label("take_count"))
        .join(Take, Take.session_id == PracticeSession.id)
        .group_by(PracticeSession.date)
        .order_by(PracticeSession.date)
        .all()
    )
    return [{"date": str(s.date), "takes": s.take_count} for s in sessions]


@router.get("/rating-trends")
def rating_trends(
    song_id: int | None = Query(None),
    dimension: str = Query("overall"),
    db: Session = Depends(get_db),
):
    """Rating values over time for a song or across all songs."""
    rating_col = getattr(Take, f"rating_{dimension}", Take.rating_overall)

    q = (
        db.query(
            PracticeSession.date,
            func.avg(rating_col).label("avg_rating"),
            func.count(Take.id).label("take_count"),
        )
        .join(Take, Take.session_id == PracticeSession.id)
        .filter(rating_col.isnot(None))
    )
    if song_id:
        q = q.filter(Take.song_id == song_id)

    results = q.group_by(PracticeSession.date).order_by(PracticeSession.date).all()

    return [{
        "date": str(r.date),
        "avg_rating": round(float(r.avg_rating), 2),
        "take_count": r.take_count,
    } for r in results]


@router.get("/skill-radar")
def skill_radar(db: Session = Depends(get_db)):
    """Average rating per dimension — for radar/spider chart."""
    dims = {}
    for dim in RATING_DIMS:
        col = getattr(Take, f"rating_{dim}")
        result = db.query(
            func.avg(col).label("avg"),
            func.count(col).label("count"),
        ).filter(col.isnot(None)).first()
        dims[dim] = {
            "average": round(float(result.avg), 2) if result.avg else None,
            "count": result.count or 0,
        }
    return dims


@router.get("/song-progress")
def song_progress(db: Session = Depends(get_db)):
    """Per-song practice stats — times practiced, latest session, avg rating."""
    results = (
        db.query(
            Song.id,
            Song.title,
            Song.type,
            Song.status,
            func.count(Take.id).label("take_count"),
            func.max(PracticeSession.date).label("last_practiced"),
            func.avg(Take.rating_overall).label("avg_rating"),
        )
        .join(Take, Take.song_id == Song.id)
        .join(PracticeSession, PracticeSession.id == Take.session_id)
        .group_by(Song.id)
        .order_by(func.count(Take.id).desc())
        .all()
    )

    return [{
        "song_id": r.id,
        "title": r.title,
        "type": r.type,
        "status": r.status,
        "take_count": r.take_count,
        "last_practiced": str(r.last_practiced) if r.last_practiced else None,
        "avg_rating": round(float(r.avg_rating), 2) if r.avg_rating else None,
    } for r in results]


@router.get("/session-summary")
def session_summary(db: Session = Depends(get_db)):
    """Per-session summary with song count and rating averages."""
    sessions = (
        db.query(
            PracticeSession.id,
            PracticeSession.date,
            func.count(Take.id).label("take_count"),
            func.count(func.nullif(Take.song_id, None)).label("matched_takes"),
            func.avg(Take.rating_overall).label("avg_overall"),
        )
        .join(Take, Take.session_id == PracticeSession.id)
        .group_by(PracticeSession.id)
        .order_by(PracticeSession.date)
        .all()
    )

    return [{
        "session_id": s.id,
        "date": str(s.date),
        "take_count": s.take_count,
        "matched_takes": s.matched_takes,
        "avg_overall": round(float(s.avg_overall), 2) if s.avg_overall else None,
    } for s in sessions]


@router.get("/status-funnel")
def status_funnel(db: Session = Depends(get_db)):
    """Songs at each status stage — shows the pipeline."""
    all_statuses = [
        "idea", "captured", "learning", "developing", "draft",
        "arranged", "rehearsed", "polished", "recorded", "released", "promoted",
    ]
    result = dict(
        db.query(Song.status, func.count()).group_by(Song.status).all()
    )
    return [{
        "status": s,
        "count": result.get(s, 0),
    } for s in all_statuses if result.get(s, 0) > 0]
