"""Recording integrity — confirm no band recordings were dropped.

Checks DB <-> storage parity in both directions:
  - DB rows (active, not soft-deleted) whose stored object is missing.
  - Storage objects with no DB row at all (uploaded but ingestion failed —
    the real "dropped recording" risk).

Read-only: reports only, never deletes.
"""

from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from app.auth.deps import require_admin
from app.config import settings
from app.database import get_db
from app.models import AudioFile
from app.services.vault import get_backend, is_cloud_backend

router = APIRouter(prefix="/api/integrity", tags=["integrity"])


@router.get("/recordings")
def check_recordings(db: Session = Depends(get_db), _user=Depends(require_admin)):
    backend = get_backend()
    cloud = is_cloud_backend()

    # All known identifiers (any role) — an object is only an "orphan" if NO
    # row references it; soft-deleted rows still own their object.
    known = {ident for (ident,) in db.query(AudioFile.identifier).all() if ident}

    # Direction 1: active DB rows whose object is gone.
    active = (
        db.query(AudioFile)
        .options(selectinload(AudioFile.song))
        .filter((AudioFile.role != "deleted") | (AudioFile.role.is_(None)))
        .all()
    )
    db_missing = []
    checked = 0
    for af in active:
        if not af.identifier or not af.file_type:
            continue
        checked += 1
        if not backend.exists(af.identifier, af.file_type):
            db_missing.append({
                "id": af.id,
                "identifier": af.identifier,
                "file_path": af.file_path,
                "song_title": af.song.title if af.song else None,
            })

    # Direction 2: storage objects with no DB row.
    orphan_objects = []
    if cloud and hasattr(backend, "list_keys"):
        for key in backend.list_keys():
            stem = Path(key).stem  # files/AF123.m4a -> AF123
            if stem and stem not in known:
                orphan_objects.append({"key": key, "identifier": stem})
    elif not cloud:
        files_dir = settings.vault_files_dir
        if files_dir.exists():
            for f in files_dir.iterdir():
                if f.is_file() and f.stem not in known:
                    orphan_objects.append({"key": f.name, "identifier": f.stem})

    return {
        "db_missing_object": db_missing,
        "orphan_objects": orphan_objects,
        "checked": checked,
        "mode": "cloud" if cloud else "local",
    }
