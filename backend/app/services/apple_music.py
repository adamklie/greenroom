"""Apple Music integration — import listening history via JXA.

Uses JavaScript for Automation (osascript -l JavaScript) to extract
track data from the Music app. Much faster than AppleScript for bulk ops.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import Base
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column


class ListeningHistory(Base):
    """Apple Music listening history — imported tracks with play counts."""
    __tablename__ = "listening_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    artist: Mapped[str] = mapped_column(String, nullable=False)
    play_count: Mapped[int] = mapped_column(Integer, default=0)
    genre: Mapped[str | None] = mapped_column(String, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_own_recording: Mapped[bool] = mapped_column(Integer, default=False)
    # Whether this track already has a corresponding Song in the catalog
    linked_song_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    imported_at: Mapped[str | None] = mapped_column(DateTime, nullable=True)


@dataclass
class AppleMusicTrack:
    title: str
    artist: str
    play_count: int
    genre: str
    duration_seconds: int


def export_from_music_app() -> list[AppleMusicTrack]:
    """Export all tracks with play count > 0 from Apple Music via JXA."""
    jxa_script = """
const Music = Application("Music");
const tracks = Music.libraryPlaylists[0].tracks();
const result = [];
for (let i = 0; i < tracks.length; i++) {
    const t = tracks[i];
    try {
        const plays = t.playedCount();
        if (plays > 0) {
            result.push([
                t.name(),
                t.artist(),
                plays,
                t.genre() || "",
                Math.round(t.duration())
            ].join("|||"));
        }
    } catch(e) {}
}
result.join("\\n");
"""
    try:
        result = subprocess.run(
            ["osascript", "-l", "JavaScript", "-e", jxa_script],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(f"JXA export failed: {result.stderr}")

        tracks = []
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|||")
            if len(parts) >= 3:
                tracks.append(AppleMusicTrack(
                    title=parts[0].strip(),
                    artist=parts[1].strip(),
                    play_count=int(parts[2]) if parts[2].isdigit() else 0,
                    genre=parts[3].strip() if len(parts) > 3 else "",
                    duration_seconds=int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0,
                ))
        return tracks

    except subprocess.TimeoutExpired:
        raise RuntimeError("Apple Music export timed out (>120s). Is the Music app responding?")
    except FileNotFoundError:
        raise RuntimeError("osascript not found — this only works on macOS")


def import_listening_history(db: Session) -> dict:
    """Import Apple Music listening history into the database.

    Returns stats about the import.
    """
    from app.models import Song

    tracks = export_from_music_app()

    # Build a lookup of existing songs by normalized title
    existing_songs = {}
    for song in db.query(Song).all():
        key = (song.title.lower().strip(), (song.artist or "").lower().strip())
        existing_songs[key] = song.id
        # Also index by title only for fuzzy matching
        existing_songs[(song.title.lower().strip(),)] = song.id

    imported = 0
    updated = 0
    linked = 0
    own_recordings = 0

    for track in tracks:
        # Check if already imported
        existing = db.query(ListeningHistory).filter_by(
            title=track.title, artist=track.artist
        ).first()

        # Is this the user's own recording? (artist contains "Adam" or matches known patterns)
        is_own = track.artist.lower() in ("adam klie", "adam", "")

        # Try to link to an existing song
        linked_id = None
        title_lower = track.title.lower().strip()
        artist_lower = track.artist.lower().strip()

        # Exact match (title + artist)
        if (title_lower, artist_lower) in existing_songs:
            linked_id = existing_songs[(title_lower, artist_lower)]
        # Title-only match
        elif (title_lower,) in existing_songs:
            linked_id = existing_songs[(title_lower,)]

        if existing:
            existing.play_count = track.play_count
            existing.genre = track.genre
            existing.is_own_recording = is_own
            existing.linked_song_id = linked_id
            updated += 1
        else:
            db.add(ListeningHistory(
                title=track.title,
                artist=track.artist,
                play_count=track.play_count,
                genre=track.genre,
                duration_seconds=track.duration_seconds,
                is_own_recording=is_own,
                linked_song_id=linked_id,
            ))
            imported += 1

        if linked_id:
            linked += 1
        if is_own:
            own_recordings += 1

    db.commit()

    total = db.query(func.count(ListeningHistory.id)).scalar()

    return {
        "total_tracks": total,
        "newly_imported": imported,
        "updated": updated,
        "linked_to_songs": linked,
        "own_recordings": own_recordings,
        "exported_from_music_app": len(tracks),
    }


def get_cover_suggestions(db: Session, limit: int = 20) -> list[dict]:
    """Suggest songs to cover based on listening history.

    Finds most-played songs that:
    - Are NOT the user's own recordings
    - Do NOT already have a corresponding Song in the catalog
    """
    from app.models import Song

    # Get all song titles we already have
    existing_titles = {s.title.lower() for s in db.query(Song.title).all()}

    suggestions = (
        db.query(ListeningHistory)
        .filter(
            ListeningHistory.is_own_recording == False,  # noqa: E712
            ListeningHistory.linked_song_id.is_(None),
        )
        .order_by(ListeningHistory.play_count.desc())
        .all()
    )

    results = []
    for track in suggestions:
        # Double-check it's not already in catalog (fuzzy)
        if track.title.lower() in existing_titles:
            continue
        results.append({
            "title": track.title,
            "artist": track.artist,
            "play_count": track.play_count,
            "genre": track.genre,
            "duration_seconds": track.duration_seconds,
        })
        if len(results) >= limit:
            break

    return results


def get_listening_stats(db: Session) -> dict:
    """Get aggregate listening statistics."""
    total = db.query(func.count(ListeningHistory.id)).scalar()
    if total == 0:
        return {"imported": False}

    total_plays = db.query(func.sum(ListeningHistory.play_count)).scalar()

    # Top artists
    top_artists = (
        db.query(
            ListeningHistory.artist,
            func.sum(ListeningHistory.play_count).label("total_plays"),
            func.count().label("track_count"),
        )
        .filter(ListeningHistory.is_own_recording == False)  # noqa: E712
        .group_by(ListeningHistory.artist)
        .order_by(func.sum(ListeningHistory.play_count).desc())
        .limit(15)
        .all()
    )

    # Top genres
    top_genres = (
        db.query(
            ListeningHistory.genre,
            func.sum(ListeningHistory.play_count).label("total_plays"),
        )
        .filter(ListeningHistory.genre != "", ListeningHistory.genre.isnot(None))
        .group_by(ListeningHistory.genre)
        .order_by(func.sum(ListeningHistory.play_count).desc())
        .limit(10)
        .all()
    )

    return {
        "imported": True,
        "total_tracks": total,
        "total_plays": total_plays,
        "top_artists": [{"artist": a, "plays": int(p), "tracks": c} for a, p, c in top_artists],
        "top_genres": [{"genre": g, "plays": int(p)} for g, p in top_genres],
    }
