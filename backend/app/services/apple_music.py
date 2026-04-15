"""Apple Music listening-history queries.

The data itself is ingested from an Apple Media Services data-export zip
via scripts/ingest_apple_dump.py. This module only queries what's in the DB.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.listening import ListeningHistory

# Genres excluded by default from "what am I actually listening to" queries.
# Toggle-able per-endpoint so you can still see the full picture.
DEFAULT_EXCLUDED_GENRES = {
    "Classical",
    "Classical Crossover",
    "Soundtrack",
    "Film Score",
    "Video Game Music",
    "Opera",
}


def _filter_genres(query, exclude_genres: set[str] | None):
    if not exclude_genres:
        return query
    return query.filter(
        (ListeningHistory.genre.is_(None)) | (~ListeningHistory.genre.in_(exclude_genres))
    )


def get_cover_suggestions(
    db: Session,
    limit: int = 20,
    exclude_genres: set[str] | None = None,
) -> list[dict]:
    """Most-played tracks not already linked to a Song in the catalog."""
    if exclude_genres is None:
        exclude_genres = DEFAULT_EXCLUDED_GENRES

    q = db.query(ListeningHistory).filter(
        ListeningHistory.is_own_recording == False,  # noqa: E712
        ListeningHistory.linked_song_id.is_(None),
    )
    q = _filter_genres(q, exclude_genres)
    rows = q.order_by(ListeningHistory.play_count.desc()).limit(limit).all()

    return [
        {
            "title": r.title,
            "artist": r.artist,
            "album": r.album,
            "genre": r.genre,
            "play_count": r.play_count,
            "total_play_ms": r.total_play_ms,
            "last_played_at": r.last_played_at.isoformat() if r.last_played_at else None,
            "duration_seconds": r.duration_seconds,
        }
        for r in rows
    ]


def get_listening_stats(
    db: Session,
    exclude_genres: set[str] | None = None,
) -> dict:
    """Aggregate listening stats, optionally filtering out classical/score genres."""
    if exclude_genres is None:
        exclude_genres = DEFAULT_EXCLUDED_GENRES

    total = db.query(func.count(ListeningHistory.id)).scalar() or 0
    if total == 0:
        return {"imported": False}

    base = _filter_genres(
        db.query(ListeningHistory).filter(ListeningHistory.is_own_recording == False),  # noqa: E712
        exclude_genres,
    )

    total_plays = base.with_entities(func.sum(ListeningHistory.play_count)).scalar() or 0
    total_ms = base.with_entities(func.sum(ListeningHistory.total_play_ms)).scalar() or 0

    top_artists = (
        base.with_entities(
            ListeningHistory.artist,
            func.sum(ListeningHistory.play_count).label("plays"),
            func.count().label("tracks"),
        )
        .group_by(ListeningHistory.artist)
        .order_by(func.sum(ListeningHistory.play_count).desc())
        .limit(15)
        .all()
    )

    top_genres = (
        db.query(
            ListeningHistory.genre,
            func.sum(ListeningHistory.play_count).label("plays"),
        )
        .filter(ListeningHistory.genre.isnot(None), ListeningHistory.genre != "")
        .group_by(ListeningHistory.genre)
        .order_by(func.sum(ListeningHistory.play_count).desc())
        .limit(15)
        .all()
    )

    return {
        "imported": True,
        "total_tracks": total,
        "total_plays": int(total_plays),
        "total_listen_hours": round(total_ms / 1000 / 3600, 1),
        "excluded_genres": sorted(exclude_genres),
        "top_artists": [
            {"artist": a, "plays": int(p), "tracks": int(c)} for a, p, c in top_artists
        ],
        "top_genres": [{"genre": g, "plays": int(p)} for g, p in top_genres],
    }
