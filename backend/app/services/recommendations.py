"""Recommendation engine for Greenroom.

Analyzes practice data, ratings, repertoire gaps, and staleness to
generate actionable recommendations for what to practice, learn, and improve.

All recommendations are data-driven from what's already in the database.
Future: Apple Music listening history adds another signal.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import AudioFile, PracticeSession, Song, Take

RATING_DIMENSIONS = ["overall", "vocals", "guitar", "drums", "tone", "timing", "energy"]


@dataclass
class Recommendation:
    category: str  # practice, learn, improve, gig, repertoire
    priority: str  # high, medium, low
    title: str
    detail: str
    song_id: int | None = None
    song_title: str | None = None
    data: dict = field(default_factory=dict)


def _days_since(d: date) -> int:
    return (date.today() - d).days


def get_recommendations(db: Session) -> list[Recommendation]:
    """Generate all recommendations from current data."""
    recs: list[Recommendation] = []

    recs.extend(_stale_songs(db))
    recs.extend(_skill_gaps(db))
    recs.extend(_unrated_takes(db))
    recs.extend(_gig_readiness(db))
    recs.extend(_repertoire_gaps(db))
    recs.extend(_idea_review(db))
    recs.extend(_recording_candidates(db))

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: priority_order.get(r.priority, 99))

    return recs


def _stale_songs(db: Session) -> list[Recommendation]:
    """Find songs that haven't been practiced recently but aren't fully polished."""
    recs = []

    # Songs with takes — find the most recent take date per song
    songs_with_takes = (
        db.query(
            Song.id, Song.title, Song.status, Song.type,
            func.max(PracticeSession.date).label("last_practiced"),
        )
        .join(Take, Take.song_id == Song.id)
        .join(PracticeSession, PracticeSession.id == Take.session_id)
        .filter(Song.status.notin_(["recorded", "released", "promoted", "archived"]))
        .group_by(Song.id)
        .all()
    )

    for song_id, title, status, song_type, last_date in songs_with_takes:
        if last_date is None:
            continue
        # Parse date - handle both string and date objects
        if isinstance(last_date, str):
            last = date.fromisoformat(last_date)
        else:
            last = last_date
        days = _days_since(last)

        if days > 28:
            recs.append(Recommendation(
                category="practice",
                priority="high" if days > 60 else "medium",
                title=f"Refresh: {title}",
                detail=f"Last practiced {days} days ago (status: {status}). Schedule a run-through to keep it sharp.",
                song_id=song_id,
                song_title=title,
                data={"days_since": days, "status": status},
            ))

    return recs


def _skill_gaps(db: Session) -> list[Recommendation]:
    """Analyze rating dimensions to find weak spots."""
    recs = []

    # Average rating per dimension across all rated takes
    dim_avgs: dict[str, float] = {}
    for dim in RATING_DIMENSIONS:
        col = getattr(Take, f"rating_{dim}")
        avg = db.query(func.avg(col)).filter(col.isnot(None)).scalar()
        if avg is not None:
            dim_avgs[dim] = float(avg)

    if not dim_avgs:
        recs.append(Recommendation(
            category="improve",
            priority="high",
            title="Start rating your takes",
            detail="You have 224 takes but none are rated yet. Rate some takes in the Sessions tab to unlock skill analysis.",
            data={},
        ))
        return recs

    if len(dim_avgs) >= 2:
        best_dim = max(dim_avgs, key=dim_avgs.get)  # type: ignore
        worst_dim = min(dim_avgs, key=dim_avgs.get)  # type: ignore
        best_avg = dim_avgs[best_dim]
        worst_avg = dim_avgs[worst_dim]

        if best_avg - worst_avg > 0.8:
            recs.append(Recommendation(
                category="improve",
                priority="high",
                title=f"Focus on {worst_dim}",
                detail=f"Your {worst_dim} ratings average {worst_avg:.1f}/5 vs {best_dim} at {best_avg:.1f}/5. Try isolating {worst_dim} in your practice.",
                data={"dimension_averages": dim_avgs},
            ))

        # Individual dimension advice
        for dim, avg in dim_avgs.items():
            if avg < 2.5:
                recs.append(Recommendation(
                    category="improve",
                    priority="medium",
                    title=f"{dim.capitalize()} needs work",
                    detail=f"Average {dim} rating is {avg:.1f}/5 across rated takes. Consider targeted exercises.",
                    data={"dimension": dim, "average": avg},
                ))

    return recs


def _unrated_takes(db: Session) -> list[Recommendation]:
    """Nudge the user to rate their takes."""
    recs = []
    total = db.query(func.count(Take.id)).scalar()
    unrated = db.query(func.count(Take.id)).filter(Take.rating_overall.is_(None)).scalar()

    if total > 0 and unrated > 0:
        pct = (unrated / total) * 100
        if pct > 80:
            recs.append(Recommendation(
                category="practice",
                priority="medium",
                title=f"Rate your takes ({unrated} unrated)",
                detail=f"{pct:.0f}% of your takes are unrated. Rating helps surface your best work and track improvement.",
                data={"total": total, "unrated": unrated, "percent": pct},
            ))

    return recs


def _gig_readiness(db: Session) -> list[Recommendation]:
    """Assess setlist readiness for different gig configurations."""
    recs = []

    # Count songs by status that are gig-ready
    polished = db.query(Song).filter(Song.status.in_(["polished", "recorded", "released"])).all()

    solo_ready = [s for s in polished if s.project in ("solo", "ozone_destructors", "sural")]
    band_ready = [s for s in polished if s.project == "ozone_destructors"]

    # Solo set needs ~12 songs for 45 min
    if len(solo_ready) < 12:
        gap = 12 - len(solo_ready)
        recs.append(Recommendation(
            category="gig",
            priority="high" if len(solo_ready) < 6 else "medium",
            title=f"Solo set: need {gap} more polished songs",
            detail=f"You have {len(solo_ready)} songs ready for a solo gig. A 45-min set needs ~12. Focus on polishing your most-practiced rehearsed songs.",
            data={"ready": len(solo_ready), "target": 12, "gap": gap},
        ))

    # Band set needs ~15 songs for 60 min
    if len(band_ready) < 15:
        gap = 15 - len(band_ready)
        recs.append(Recommendation(
            category="gig",
            priority="medium",
            title=f"Band set: need {gap} more polished songs",
            detail=f"Ozone Destructors has {len(band_ready)} polished songs. A 60-min set needs ~15.",
            data={"ready": len(band_ready), "target": 15, "gap": gap},
        ))

    return recs


def _repertoire_gaps(db: Session) -> list[Recommendation]:
    """Analyze key, genre, and tempo distribution for gaps."""
    recs = []

    # Key distribution
    keys = (
        db.query(Song.key, func.count())
        .filter(Song.key.isnot(None), Song.key != "")
        .group_by(Song.key)
        .all()
    )
    songs_with_keys = sum(c for _, c in keys)
    songs_without_keys = db.query(func.count(Song.id)).filter(
        (Song.key.is_(None)) | (Song.key == "")
    ).scalar()

    if songs_without_keys > 20:
        recs.append(Recommendation(
            category="repertoire",
            priority="low",
            title=f"Add keys to {songs_without_keys} songs",
            detail="Knowing the key of each song helps with setlist planning (avoid too many songs in the same key).",
            data={"songs_without_keys": songs_without_keys},
        ))

    # Type balance
    cover_count = db.query(func.count(Song.id)).filter(Song.type == "cover").scalar()
    original_count = db.query(func.count(Song.id)).filter(Song.type == "original").scalar()

    if original_count > 0 and cover_count > original_count * 5:
        recs.append(Recommendation(
            category="repertoire",
            priority="low",
            title="Write more originals",
            detail=f"You have {cover_count} covers but only {original_count} originals. Originals build your identity.",
            data={"covers": cover_count, "originals": original_count},
        ))

    return recs


def _idea_review(db: Session) -> list[Recommendation]:
    """Surface old ideas that should be developed or archived."""
    recs = []

    ideas = db.query(Song).filter(
        Song.type == "idea",
        Song.status.notin_(["promoted", "archived"]),
    ).all()

    stale_ideas = [s for s in ideas if s.created_at and _days_since(s.created_at.date()) > 90]

    if len(stale_ideas) > 3:
        recs.append(Recommendation(
            category="repertoire",
            priority="low",
            title=f"Review {len(stale_ideas)} old ideas",
            detail="Some ideas have been sitting for 3+ months. Promote the promising ones to originals or archive the rest.",
            data={"stale_count": len(stale_ideas)},
        ))

    return recs


def _recording_candidates(db: Session) -> list[Recommendation]:
    """Find polished songs that should be recorded."""
    recs = []

    polished_unrecorded = (
        db.query(Song)
        .filter(Song.status == "polished")
        .all()
    )

    for song in polished_unrecorded[:3]:  # Top 3
        recs.append(Recommendation(
            category="practice",
            priority="medium",
            title=f"Record: {song.title}",
            detail=f"'{song.title}' is polished — time to record a proper version for your portfolio.",
            song_id=song.id,
            song_title=song.title,
            data={},
        ))

    return recs
