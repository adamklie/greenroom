"""Bootstrap the database from the filesystem.

Run via: python -m app.services.bootstrap
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import (
    AudioFile, PracticeSession, Song, Tag, Take, TriageItem,
    PREDEFINED_TAGS,
)
from app.services.markdown_parser import parse_repertoire
from app.services.media_scanner import scan_media
from app.services.session_scanner import scan_sessions


def _normalize_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def _clip_to_song_name(clip_name: str) -> str:
    name = re.sub(r"\.\w{2,4}$", "", clip_name)
    name = re.sub(r"_(\d+)$", "", name)
    name = name.replace("_", " ")
    return _normalize_name(name)


_ALIASES = {
    "middle": "the middle",
    "sugar were": "sugar were goin down",
    "say it aint": "say it aint so",
    "girl is acoustic": "girl is on my mind",
    "girl is on mind": "girl is on my mind",
}


def _match_clip_to_song(clip_name: str, songs_by_norm: dict[str, Song]) -> Song | None:
    norm = _clip_to_song_name(clip_name)
    norm = re.sub(r"\.mp4$", "", norm)
    if norm in songs_by_norm:
        return songs_by_norm[norm]
    if norm in _ALIASES and _ALIASES[norm] in songs_by_norm:
        return songs_by_norm[_ALIASES[norm]]
    for song_norm, song in songs_by_norm.items():
        if norm in song_norm or song_norm in norm:
            return song
    return None


def _derive_song_type(project: str, is_original: bool, status: str) -> str:
    """Derive song type from existing data."""
    if project == "ideas":
        return "idea"
    if is_original:
        return "original"
    return "cover"


def bootstrap_tags(db: DBSession) -> None:
    """Seed predefined tags if they don't exist."""
    for tag_data in PREDEFINED_TAGS:
        existing = db.query(Tag).filter_by(name=tag_data["name"]).first()
        if not existing:
            db.add(Tag(
                name=tag_data["name"],
                category=tag_data["category"],
                is_predefined=True,
            ))


def bootstrap_songs(db: DBSession) -> dict[str, Song]:
    """Parse REPERTOIRE.md and insert NEW songs. Returns normalized name → Song map.

    REPERTOIRE.md is a seed, not a source of truth. If a Song row already
    exists for a given (title, project), this function leaves it untouched —
    ongoing edits to artist / type / status / notes happen in the UI and
    would otherwise be clobbered on the next bootstrap.
    """
    repertoire_path = settings.music_dir / "REPERTOIRE.md"
    if not repertoire_path.exists():
        print("  REPERTOIRE.md not found, skipping")
        return {}

    parsed = parse_repertoire(repertoire_path)
    songs_by_norm: dict[str, Song] = {}

    for p in parsed:
        norm = _normalize_name(p.title)
        song_type = _derive_song_type(p.project, p.is_original, p.status)

        existing = db.query(Song).filter_by(title=p.title, project=p.project).first()

        if existing:
            # Song already exists — preserve every field the user may have
            # edited. We still include it in the returned map so later
            # bootstrap phases (sessions, media) can still match clips to it.
            songs_by_norm[norm] = existing
        else:
            song = Song(
                title=p.title,
                artist=p.artist,
                project=p.project,
                is_original=p.is_original,
                type=song_type,
                status=p.status,
                times_practiced=p.times_practiced,
                notes=p.notes,
            )
            db.add(song)
            db.flush()
            songs_by_norm[norm] = song

    return songs_by_norm


def bootstrap_sessions(db: DBSession, songs_by_norm: dict[str, Song]) -> tuple[int, int]:
    """Scan practice sessions and insert/update."""
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
                # Don't overwrite video_path / audio_path — the user may have
                # moved files via the file manager, and re-scanning should
                # never revert that. Only fill fields that are currently null.
                if not existing_take.video_path:
                    existing_take.video_path = pt.video_path
                if not existing_take.audio_path:
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


def bootstrap_media(db: DBSession, songs_by_norm: dict[str, Song]) -> tuple[int, int]:
    """Scan audio files. Returns (matched_count, triage_count)."""
    parsed_files = scan_media(settings.music_dir)
    matched_count = 0
    triage_count = 0

    for pf in parsed_files:
        # Skip stems
        if pf.is_stem:
            continue

        existing = db.query(AudioFile).filter_by(file_path=pf.file_path).first()
        if existing:
            continue

        # Try to match to a song
        norm_hint = _normalize_name(pf.song_title_hint)
        matched = songs_by_norm.get(norm_hint)

        # Try substring matching if exact fails
        if not matched:
            for song_norm, song in songs_by_norm.items():
                if norm_hint in song_norm or song_norm in norm_hint:
                    matched = song
                    break

        from pathlib import Path as _Path
        from app.models.audio_file import generate_identifier
        orig_name = _Path(pf.file_path).name
        af = AudioFile(
            song_id=matched.id if matched else None,
            file_path=pf.file_path,
            file_type=pf.file_type,
            identifier=generate_identifier(orig_name),
            submitted_file_name=orig_name,
            source=pf.source,
            role=pf.role,
            version=pf.version,
            is_stem=pf.is_stem,
        )
        db.add(af)

        if matched:
            matched_count += 1
        else:
            # Add to triage queue
            existing_triage = db.query(TriageItem).filter_by(file_path=pf.file_path).first()
            if not existing_triage:
                db.add(TriageItem(
                    file_path=pf.file_path,
                    file_type=pf.file_type,
                    suggested_source=pf.source,
                ))
                triage_count += 1

    return matched_count, triage_count


def run_bootstrap():
    """Run the full bootstrap process."""
    print("Greenroom v2 Bootstrap")
    print(f"Music directory: {settings.music_dir}")
    print(f"Database: {settings.db_path}")
    print()

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        print("1. Seeding tags...")
        bootstrap_tags(db)
        db.commit()
        tag_count = db.query(Tag).count()
        print(f"   {tag_count} tags")

        print("2. Parsing REPERTOIRE.md...")
        songs_by_norm = bootstrap_songs(db)
        db.commit()
        print(f"   {len(songs_by_norm)} songs")

        # Show type breakdown
        for song_type in ["cover", "original", "idea"]:
            count = db.query(Song).filter(Song.type == song_type).count()
            print(f"     {song_type}: {count}")

        print("3. Scanning practice sessions...")
        sess_count, take_count = bootstrap_sessions(db, songs_by_norm)
        db.commit()
        total_sessions = db.query(PracticeSession).count()
        total_takes = db.query(Take).count()
        matched_takes = db.query(Take).filter(Take.song_id.isnot(None)).count()
        print(f"   {total_sessions} sessions, {total_takes} takes ({matched_takes} matched)")

        print("4. Scanning audio files...")
        matched, triaged = bootstrap_media(db, songs_by_norm)
        db.commit()
        total_audio = db.query(AudioFile).count()
        total_triage = db.query(TriageItem).count()
        print(f"   {total_audio} audio files ({matched} matched)")
        print(f"   {total_triage} items in triage queue")

        print()
        print("Bootstrap complete!")
    finally:
        db.close()


if __name__ == "__main__":
    run_bootstrap()
