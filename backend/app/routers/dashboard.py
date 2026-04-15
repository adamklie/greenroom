from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AudioFile, PracticeSession, Song, Take, TriageItem
from app.schemas.dashboard import (
    DashboardResponse,
    DashboardStats,
    RecentAudioFile,
    RecentSession,
    RecentSong,
)

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
    unrated_audio = db.query(func.count(AudioFile.id)).filter(
        AudioFile.rating_overall.is_(None),
        AudioFile.is_stem == False,  # noqa: E712
    ).scalar()
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
        unrated_audio_files=unrated_audio,
        triage_pending=triage_pending,
    )

    recent_songs_rows = (
        db.query(Song).filter(Song.status != "deleted")
        .order_by(Song.created_at.desc()).limit(10).all()
    )
    recent_songs = [
        RecentSong(
            id=s.id, title=s.title, artist=s.artist, type=s.type, status=s.status,
            created_at=s.created_at.isoformat() if s.created_at else None,
        ) for s in recent_songs_rows
    ]

    recent_af_rows = (
        db.query(AudioFile)
        .order_by(AudioFile.created_at.desc()).limit(10).all()
    )
    recent_audio_files = [
        RecentAudioFile(
            id=af.id, identifier=af.identifier, file_path=af.file_path,
            file_type=af.file_type, song_id=af.song_id,
            song_title=af.song.title if af.song else None,
            session_id=af.session_id,
            session_date=str(af.session.date) if af.session else None,
            created_at=af.created_at.isoformat() if af.created_at else None,
            uploaded_at=af.uploaded_at.isoformat() if af.uploaded_at else None,
            recorded_at=af.recorded_at.isoformat() if af.recorded_at else None,
        ) for af in recent_af_rows
    ]

    recent_sess_rows = (
        db.query(PracticeSession)
        .order_by(PracticeSession.created_at.desc()).limit(5).all()
    )
    recent_sessions = [
        RecentSession(
            id=s.id, date=str(s.date), folder_path=s.folder_path,
            clip_count=db.query(func.count(AudioFile.id))
                .filter(AudioFile.session_id == s.id).scalar() or 0,
            created_at=s.created_at.isoformat() if s.created_at else None,
        ) for s in recent_sess_rows
    ]

    return DashboardResponse(
        stats=stats,
        recent_songs=recent_songs,
        recent_audio_files=recent_audio_files,
        recent_sessions=recent_sessions,
    )
