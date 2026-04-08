"""Bootstrap the database from the filesystem.

Run via: python -m app.services.bootstrap
"""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import AudioFile, PracticeSession, RoadmapTask, Song, Take
from app.services.markdown_parser import parse_repertoire, parse_roadmap
from app.services.media_scanner import scan_media
from app.services.session_scanner import scan_sessions


def _normalize_name(name: str) -> str:
    """Normalize a song name for fuzzy matching."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def _clip_to_song_name(clip_name: str) -> str:
    """Convert a clip name like 'smells_like_teen_spirit_2' to a normalized song name."""
    # Strip file extension if present
    name = re.sub(r"\.\w{2,4}$", "", clip_name)
    # Strip trailing _N (take numbers)
    name = re.sub(r"_(\d+)$", "", name)
    name = name.replace("_", " ")
    return _normalize_name(name)


def _match_clip_to_song(clip_name: str, songs_by_norm: dict[str, Song]) -> Song | None:
    """Try to match a clip name to a song in the database."""
    norm = _clip_to_song_name(clip_name)

    # Strip ".mp4" suffix if present
    norm = re.sub(r"\.mp4$", "", norm)

    # Exact match
    if norm in songs_by_norm:
        return songs_by_norm[norm]

    # Common abbreviation expansions
    _ALIASES = {
        "middle": "the middle",
        "sugar were": "sugar were goin down",
        "say it aint": "say it aint so",
        "girl is acoustic": "girl is on my mind",
        "girl is on mind": "girl is on my mind",
    }
    if norm in _ALIASES and _ALIASES[norm] in songs_by_norm:
        return songs_by_norm[_ALIASES[norm]]

    # Substring match (clip name contained in song name or vice versa)
    for song_norm, song in songs_by_norm.items():
        if norm in song_norm or song_norm in norm:
            return song

    return None


def bootstrap_songs(db: Session) -> dict[str, Song]:
    """Parse REPERTOIRE.md and insert/update songs. Returns normalized name → Song map."""
    repertoire_path = settings.music_dir / "REPERTOIRE.md"
    if not repertoire_path.exists():
        print("  REPERTOIRE.md not found, skipping")
        return {}

    parsed = parse_repertoire(repertoire_path)
    songs_by_norm: dict[str, Song] = {}

    for p in parsed:
        norm = _normalize_name(p.title)
        existing = db.query(Song).filter_by(title=p.title, project=p.project).first()

        if existing:
            existing.artist = p.artist
            existing.is_original = p.is_original
            existing.status = p.status
            existing.times_practiced = p.times_practiced
            existing.notes = p.notes
            existing.updated_at = datetime.now()
            songs_by_norm[norm] = existing
        else:
            song = Song(
                title=p.title,
                artist=p.artist,
                project=p.project,
                is_original=p.is_original,
                status=p.status,
                times_practiced=p.times_practiced,
                notes=p.notes,
            )
            db.add(song)
            db.flush()
            songs_by_norm[norm] = song

    return songs_by_norm


def bootstrap_roadmap(db: Session) -> int:
    """Parse ROADMAP.md and insert/update tasks. Returns count."""
    roadmap_path = settings.music_dir / "ROADMAP.md"
    if not roadmap_path.exists():
        print("  ROADMAP.md not found, skipping")
        return 0

    parsed = parse_roadmap(roadmap_path)

    # Clear and re-insert (roadmap is small and changes frequently)
    db.query(RoadmapTask).delete()

    for p in parsed:
        db.add(RoadmapTask(
            phase=p.phase,
            phase_title=p.phase_title,
            category=p.category,
            task_text=p.task_text,
            completed=p.completed,
            sort_order=p.sort_order,
        ))

    return len(parsed)


def bootstrap_sessions(db: Session, songs_by_norm: dict[str, Song]) -> tuple[int, int]:
    """Scan practice sessions and insert/update. Returns (session_count, take_count)."""
    parsed_sessions = scan_sessions(settings.music_dir)
    session_count = 0
    take_count = 0

    for ps in parsed_sessions:
        existing = db.query(PracticeSession).filter_by(folder_path=ps.folder_path).first()

        if existing:
            session = existing
        else:
            session = PracticeSession(
                date=ps.session_date,
                project=ps.project,
                folder_path=ps.folder_path,
            )
            db.add(session)
            db.flush()
            session_count += 1

        for pt in ps.takes:
            existing_take = db.query(Take).filter_by(
                session_id=session.id, clip_name=pt.clip_name
            ).first()

            if existing_take:
                # Update paths if they changed
                existing_take.video_path = pt.video_path
                existing_take.audio_path = pt.audio_path
                if not existing_take.song_id:
                    matched = _match_clip_to_song(pt.clip_name, songs_by_norm)
                    if matched:
                        existing_take.song_id = matched.id
            else:
                matched = _match_clip_to_song(pt.clip_name, songs_by_norm)
                take = Take(
                    session_id=session.id,
                    song_id=matched.id if matched else None,
                    clip_name=pt.clip_name,
                    source_video=pt.source_video,
                    start_time=pt.start_time,
                    end_time=pt.end_time,
                    video_path=pt.video_path,
                    audio_path=pt.audio_path,
                )
                db.add(take)
                take_count += 1

    return session_count, take_count


def bootstrap_media(db: Session, songs_by_norm: dict[str, Song]) -> int:
    """Scan standalone audio files and insert/update. Returns count."""
    parsed_files = scan_media(settings.music_dir)
    count = 0

    for pf in parsed_files:
        existing = db.query(AudioFile).filter_by(file_path=pf.file_path).first()
        if existing:
            continue

        # Try to match to a song
        norm_hint = _normalize_name(pf.song_title_hint)
        matched = songs_by_norm.get(norm_hint)

        af = AudioFile(
            song_id=matched.id if matched else None,
            file_path=pf.file_path,
            file_type=pf.file_type,
            source=pf.source,
            version=pf.version,
        )
        db.add(af)
        count += 1

    return count


def run_bootstrap():
    """Run the full bootstrap process."""
    print("Greenroom Bootstrap")
    print(f"Music directory: {settings.music_dir}")
    print(f"Database: {settings.db_path}")
    print()

    # Create tables
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("1. Parsing REPERTOIRE.md...")
        songs_by_norm = bootstrap_songs(db)
        db.commit()
        print(f"   {len(songs_by_norm)} songs")

        print("2. Parsing ROADMAP.md...")
        task_count = bootstrap_roadmap(db)
        db.commit()
        print(f"   {task_count} tasks")

        print("3. Scanning practice sessions...")
        sess_count, take_count = bootstrap_sessions(db, songs_by_norm)
        db.commit()
        total_sessions = db.query(PracticeSession).count()
        total_takes = db.query(Take).count()
        matched_takes = db.query(Take).filter(Take.song_id.isnot(None)).count()
        print(f"   {total_sessions} sessions, {total_takes} takes ({matched_takes} matched to songs)")

        print("4. Scanning audio files...")
        media_count = bootstrap_media(db, songs_by_norm)
        db.commit()
        total_audio = db.query(AudioFile).count()
        matched_audio = db.query(AudioFile).filter(AudioFile.song_id.isnot(None)).count()
        print(f"   {total_audio} audio files ({matched_audio} matched to songs)")

        print()
        print("Bootstrap complete!")
    finally:
        db.close()


if __name__ == "__main__":
    run_bootstrap()
