"""Songs CRUD — the three pillars: covers, originals, ideas."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.deps import project_editor, project_viewer
from app.config import settings
from app.database import get_db
from app.models import AudioFile, LyricsVersion, Song, Tag, Take
from app.schemas.audio_file import AudioFileRead, AudioFileUpdate
from app.schemas.audio_file import AudioFileRead
from app.schemas.lyrics_version import LyricsUpdate, LyricsVersionRead
from app.schemas.song import SongCreate, SongDetail, SongRead, SongUpdate
from app.schemas.take import TakeRead

router = APIRouter(prefix="/api/songs", tags=["songs"])


def _require_accessible_audio_file(audio_file_id: int | None, db: Session) -> None:
    """Reject a reference_audio_file_id that points outside the active project.
    A written FK isn't covered by the read filter, so validate it via a scoped
    lookup (returns None for a cross-project row)."""
    if audio_file_id is not None and db.query(AudioFile).get(audio_file_id) is None:
        raise HTTPException(400, "reference_audio_file_id refers to a file you can't access")


def _require_accessible_song(song_id: int | None, db: Session) -> None:
    """Reject reassigning an audio file to a song outside the active project."""
    if song_id is not None and db.query(Song).get(song_id) is None:
        raise HTTPException(400, "song_id refers to a song you can't access")


def _songs_to_read_bulk(songs: list[Song], db: Session) -> list[SongRead]:
    """Build SongRead list with a handful of aggregate queries instead of N+1."""
    if not songs:
        return []
    ids = [s.id for s in songs]

    # One-shot aggregates
    af_counts = dict(
        db.query(AudioFile.song_id, func.count(AudioFile.id))
        .filter(AudioFile.song_id.in_(ids))
        .group_by(AudioFile.song_id).all()
    )
    # Tags are already eager-loaded via the Song.tags relationship (default lazy).
    # Access via song.tags in the loop; ensure the relationship is loaded up-front.
    results: list[SongRead] = []
    for song in songs:
        track_count = af_counts.get(song.id, 0)
        results.append(SongRead(
            id=song.id, title=song.title, artist=song.artist, type=song.type,
            project=song.project, status=song.status, key=song.key,
            tempo_bpm=song.tempo_bpm, tuning=song.tuning, vibe=song.vibe,
            lyrics=song.lyrics, notes=song.notes,
            times_practiced=song.times_practiced,
            reference_audio_file_id=song.reference_audio_file_id,
            promoted_from_id=song.promoted_from_id,
            created_at=song.created_at, updated_at=song.updated_at,
            has_audio=track_count > 0,
            track_count=track_count,
            tags=[t.name for t in song.tags],
        ))
    return results


def _song_to_read(song: Song, db: Session) -> SongRead:
    has_audio = db.query(AudioFile.id).filter(AudioFile.song_id == song.id).first() is not None
    track_count = db.query(func.count(AudioFile.id)).filter(AudioFile.song_id == song.id).scalar()
    tag_names = [t.name for t in song.tags]
    return SongRead(
        id=song.id,
        title=song.title,
        artist=song.artist,
        type=song.type,
        project=song.project,
        status=song.status,
        key=song.key,
        tempo_bpm=song.tempo_bpm,
        tuning=song.tuning,
        vibe=song.vibe,
        lyrics=song.lyrics,
        notes=song.notes,
        times_practiced=song.times_practiced,
        reference_audio_file_id=song.reference_audio_file_id,
        promoted_from_id=song.promoted_from_id,
        created_at=song.created_at,
        updated_at=song.updated_at,
        has_audio=has_audio,
        track_count=track_count,
        tags=tag_names,
    )


@router.get("", response_model=list[SongRead])
def list_songs(
    type: str | None = Query(None),
    project: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    tag: str | None = Query(None),
    include_deleted: bool = Query(False),
    db: Session = Depends(get_db),
    _user=Depends(project_viewer),
):
    q = db.query(Song)
    if not include_deleted:
        q = q.filter(Song.status != "deleted")
    if type:
        q = q.filter(Song.type == type)
    if project:
        q = q.filter(Song.project == project)
    if status:
        q = q.filter(Song.status == status)
    if search:
        q = q.filter(
            Song.title.ilike(f"%{search}%") | Song.artist.ilike(f"%{search}%")
        )
    if tag:
        q = q.filter(Song.tags.any(Tag.name == tag))
    songs = q.order_by(Song.times_practiced.desc(), Song.title).all()
    return _songs_to_read_bulk(songs, db)


@router.post("", response_model=SongRead)
def create_song(data: SongCreate, db: Session = Depends(get_db), _user=Depends(project_editor)):
    values = data.model_dump()
    # DB has NOT NULL on type/status/project from original schema — provide defaults
    if not values.get("type"):
        values["type"] = "idea"
    if not values.get("status"):
        values["status"] = "idea"
    if not values.get("project"):
        values["project"] = "solo"
    song = Song(**values)
    db.add(song)
    db.commit()
    db.refresh(song)
    return _song_to_read(song, db)


@router.get("/{song_id}", response_model=SongDetail)
def get_song(song_id: int, db: Session = Depends(get_db), _user=Depends(project_viewer)):
    song = db.query(Song).get(song_id)
    if not song:
        raise HTTPException(404, "Song not found")

    takes = db.query(Take).filter(Take.song_id == song_id).all()
    audio_files = (
        db.query(AudioFile)
        .filter(AudioFile.song_id == song_id)
        .order_by(AudioFile.recorded_at.desc().nullslast(), AudioFile.uploaded_at.desc().nullslast())
        .all()
    )
    lyrics_versions = (
        db.query(LyricsVersion)
        .filter(LyricsVersion.song_id == song_id)
        .order_by(LyricsVersion.version_number.desc())
        .all()
    )

    take_reads = []
    for t in takes:
        tr = TakeRead.model_validate(t)
        tr.tags = [tg.name for tg in t.tags]
        if t.session:
            tr.session_date = str(t.session.date)
        take_reads.append(tr)

    base = _song_to_read(song, db)
    return SongDetail(
        **base.model_dump(),
        takes=take_reads,
        audio_files=[AudioFileRead.model_validate(a) for a in audio_files],
        lyrics_versions=[LyricsVersionRead.model_validate(lv) for lv in lyrics_versions],
    )


@router.patch("/{song_id}", response_model=SongRead)
def update_song(song_id: int, data: SongUpdate, db: Session = Depends(get_db), _user=Depends(project_editor)):
    song = db.query(Song).get(song_id)
    if not song:
        raise HTTPException(404, "Song not found")

    # Track which fields changed (for auto-sync)
    changes = data.model_dump(exclude_unset=True)
    if "reference_audio_file_id" in changes:
        _require_accessible_audio_file(changes["reference_audio_file_id"], db)
    needs_file_sync = any(k in changes for k in ("type", "project", "title", "artist"))

    for field, value in changes.items():
        setattr(song, field, value)
    song.updated_at = datetime.now()
    db.commit()
    db.refresh(song)

    # Auto-sync: if type/project/title/artist changed, move files to match.
    # Cloud mode: skip the filesystem move — R2 objects are content-addressed
    # by identifier and don't live in a human-browsable folder tree.
    if needs_file_sync:
        from app.services.vault import is_cloud_backend
        if not is_cloud_backend():
            from app.services.autosync import sync_song_files
            sync_song_files(db, song)
            db.commit()

    return _song_to_read(song, db)


@router.delete("/{song_id}")
def delete_song(song_id: int, db: Session = Depends(get_db), _user=Depends(project_editor)):
    """Soft-delete: moves files to _trash/, marks song as deleted.
    Files are permanently removed after 30 days."""
    from app.services.autosync import soft_delete_song
    try:
        result = soft_delete_song(db, song_id)
        return {"ok": True, "soft_deleted": True, **result}
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/{song_id}/restore", response_model=SongRead)
def restore_deleted_song(song_id: int, db: Session = Depends(get_db), _user=Depends(project_editor)):
    """Restore a soft-deleted song."""
    from app.services.autosync import restore_song
    try:
        restore_song(db, song_id)
        song = db.query(Song).get(song_id)
        return _song_to_read(song, db)
    except ValueError as e:
        raise HTTPException(404, str(e))


# --- Lyrics ---

@router.put("/{song_id}/lyrics", response_model=SongRead)
def update_lyrics(song_id: int, data: LyricsUpdate, db: Session = Depends(get_db), _user=Depends(project_editor)):
    song = db.query(Song).get(song_id)
    if not song:
        raise HTTPException(404, "Song not found")

    # Version the old lyrics if they exist
    if song.lyrics:
        max_ver = (
            db.query(func.max(LyricsVersion.version_number))
            .filter(LyricsVersion.song_id == song_id)
            .scalar()
        ) or 0
        db.add(LyricsVersion(
            song_id=song_id,
            version_number=max_ver + 1,
            lyrics_text=song.lyrics,
            change_note=data.change_note,
        ))

    song.lyrics = data.lyrics
    song.updated_at = datetime.now()
    db.commit()
    db.refresh(song)
    return _song_to_read(song, db)


@router.get("/{song_id}/lyrics/versions", response_model=list[LyricsVersionRead])
def list_lyrics_versions(song_id: int, db: Session = Depends(get_db), _user=Depends(project_viewer)):
    return (
        db.query(LyricsVersion)
        .filter(LyricsVersion.song_id == song_id)
        .order_by(LyricsVersion.version_number.desc())
        .all()
    )


# --- Tags ---

@router.post("/{song_id}/tags")
def add_song_tag(song_id: int, tag_name: str = Query(...), db: Session = Depends(get_db), _user=Depends(project_editor)):
    song = db.query(Song).get(song_id)
    if not song:
        raise HTTPException(404, "Song not found")
    tag = db.query(Tag).filter_by(name=tag_name).first()
    if not tag:
        tag = Tag(name=tag_name, category="song", is_predefined=False)
        db.add(tag)
        db.flush()
    if tag not in song.tags:
        song.tags.append(tag)
    db.commit()
    return {"ok": True, "tags": [t.name for t in song.tags]}


@router.delete("/{song_id}/tags/{tag_name}")
def remove_song_tag(song_id: int, tag_name: str, db: Session = Depends(get_db), _user=Depends(project_editor)):
    song = db.query(Song).get(song_id)
    if not song:
        raise HTTPException(404, "Song not found")
    tag = db.query(Tag).filter_by(name=tag_name).first()
    if tag and tag in song.tags:
        song.tags.remove(tag)
    db.commit()
    return {"ok": True, "tags": [t.name for t in song.tags]}


# --- Promote idea to original ---

@router.post("/{song_id}/promote", response_model=SongRead)
def promote_idea(song_id: int, db: Session = Depends(get_db), _user=Depends(project_editor)):
    song = db.query(Song).get(song_id)
    if not song:
        raise HTTPException(404, "Song not found")
    if song.type != "idea":
        raise HTTPException(400, "Only ideas can be promoted")

    new_song = Song(
        title=song.title,
        artist=None,
        type="original",
        project=song.project,
        status="idea",
        key=song.key,
        tempo_bpm=song.tempo_bpm,
        tuning=song.tuning,
        vibe=song.vibe,
        lyrics=song.lyrics,
        notes=song.notes,
        promoted_from_id=song.id,
    )
    db.add(new_song)

    song.status = "promoted"
    song.updated_at = datetime.now()

    db.commit()
    db.refresh(new_song)
    return _song_to_read(new_song, db)


# --- Audio File CRUD ---

@router.patch("/audio-files/{audio_file_id}", response_model=AudioFileRead)
def update_audio_file(audio_file_id: int, data: AudioFileUpdate, db: Session = Depends(get_db), _user=Depends(project_editor)):
    """Update an audio file's metadata. If song_id changes, file moves automatically."""
    af = db.query(AudioFile).get(audio_file_id)
    if not af:
        raise HTTPException(404, "Audio file not found")

    changes = data.model_dump(exclude_unset=True)
    if "song_id" in changes:
        _require_accessible_song(changes["song_id"], db)
    song_changed = "song_id" in changes and changes["song_id"] != af.song_id

    for field, value in changes.items():
        setattr(af, field, value)

    db.commit()
    db.refresh(af)

    # If linked to a (new) song, move file to that song's organized location.
    # Cloud mode: R2 objects are content-addressed by identifier; no move needed.
    if song_changed and af.song_id:
        from app.services.vault import is_cloud_backend
        if not is_cloud_backend():
            song = db.query(Song).get(af.song_id)
            if song:
                from app.services.autosync import compute_organized_path, resolve_path
                import shutil

                current_full = resolve_path(af.file_path)
                if current_full.exists():
                    target_rel = compute_organized_path(song, current_full.name)
                    target_full = settings.music_dir / target_rel

                    if str(current_full) != str(target_full):
                        target_full.parent.mkdir(parents=True, exist_ok=True)
                        if not target_full.exists():
                            shutil.move(str(current_full), str(target_full))
                            af.file_path = target_rel
                            db.commit()

                            # Clean up empty parent
                            from app.services.autosync import _cleanup_empty_parent
                            _cleanup_empty_parent(current_full.parent)

    return AudioFileRead.model_validate(af)
