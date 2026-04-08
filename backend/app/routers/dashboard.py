from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AudioFile, PracticeSession, RoadmapTask, Song, Take
from app.schemas.dashboard import DashboardResponse, DashboardStats
from app.schemas.roadmap import RoadmapPhase, RoadmapTaskRead

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardResponse)
def get_dashboard(db: Session = Depends(get_db)):
    # Stats
    total_songs = db.query(func.count(Song.id)).scalar()
    total_sessions = db.query(func.count(PracticeSession.id)).scalar()
    total_takes = db.query(func.count(Take.id)).scalar()
    total_audio = db.query(func.count(AudioFile.id)).scalar()

    songs_by_status = dict(
        db.query(Song.status, func.count()).group_by(Song.status).all()
    )
    songs_by_project = dict(
        db.query(Song.project, func.count()).group_by(Song.project).all()
    )
    gig_ready = db.query(func.count(Song.id)).filter(
        Song.status.in_(["polished", "recorded", "released"])
    ).scalar()
    unrated = db.query(func.count(Take.id)).filter(Take.rating.is_(None)).scalar()

    stats = DashboardStats(
        total_songs=total_songs,
        total_sessions=total_sessions,
        total_takes=total_takes,
        total_audio_files=total_audio,
        songs_by_status=songs_by_status,
        songs_by_project=songs_by_project,
        gig_ready_songs=gig_ready,
        unrated_takes=unrated,
    )

    # Roadmap grouped by phase
    all_tasks = db.query(RoadmapTask).order_by(RoadmapTask.sort_order).all()
    phases_map: dict[int, RoadmapPhase] = {}
    for t in all_tasks:
        if t.phase not in phases_map:
            phases_map[t.phase] = RoadmapPhase(
                phase=t.phase,
                phase_title=t.phase_title or f"Phase {t.phase}",
                tasks=[],
                total=0,
                completed=0,
            )
        p = phases_map[t.phase]
        p.tasks.append(RoadmapTaskRead.model_validate(t))
        p.total += 1
        if t.completed:
            p.completed += 1

    roadmap = [phases_map[k] for k in sorted(phases_map)]

    return DashboardResponse(stats=stats, roadmap=roadmap)
