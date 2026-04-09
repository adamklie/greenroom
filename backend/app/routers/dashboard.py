from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AudioFile, PracticeSession, Song, Take, TriageItem
from app.schemas.dashboard import DashboardResponse, DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    total_songs = db.query(func.count(Song.id)).scalar()
    total_sessions = db.query(func.count(PracticeSession.id)).scalar()
    total_takes = db.query(func.count(Take.id)).scalar()
    total_audio = db.query(func.count(AudioFile.id)).scalar()

    songs_by_type = dict(
        db.query(Song.type, func.count()).group_by(Song.type).all()
    )
    songs_by_status = dict(
        db.query(Song.status, func.count()).group_by(Song.status).all()
    )
    songs_by_project = dict(
        db.query(Song.project, func.count()).group_by(Song.project).all()
    )
    unrated = db.query(func.count(Take.id)).filter(Take.rating_overall.is_(None)).scalar()
    triage_pending = db.query(func.count(TriageItem.id)).filter(
        TriageItem.status == "pending"
    ).scalar()

    stats = DashboardStats(
        total_songs=total_songs,
        total_sessions=total_sessions,
        total_takes=total_takes,
        total_audio_files=total_audio,
        songs_by_type=songs_by_type,
        songs_by_status=songs_by_status,
        songs_by_project=songs_by_project,
        unrated_takes=unrated,
        triage_pending=triage_pending,
    )

    return DashboardResponse(stats=stats)
