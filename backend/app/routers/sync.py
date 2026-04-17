"""Sync API: export annotations + back up the DB to the vault.

Under the vault architecture, audio files live in iCloud and don't need
rescanning or hashing as a maintenance chore — the only things that need
periodic snapshotting are the annotation export (portable JSON) and the
live DB (used for one-click rollback).

Filesystem rescan used to live here; it's been retired from the sync
workflow. If/when a new adaptive-import feature lands, it will have its
own surface.
"""

import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AudioFile, PracticeSession, Song, Take, TriageItem
from app.services.backup import backup_database, export_annotations, list_backups

router = APIRouter(prefix="/api/sync", tags=["sync"])


def _export_annotations_to_vault(db: Session) -> dict:
    result = export_annotations(db)
    settings.ensure_vault_layout()
    (settings.vault_exports_dir / "annotations_latest.json").write_text(
        json.dumps(result["data"], indent=2)
    )
    return result["data"]


@router.post("/after-practice")
def after_practice(db: Session = Depends(get_db)):
    """Snapshot annotations + back up the DB. Runs quickly; no filesystem scan."""
    steps = []

    try:
        data = _export_annotations_to_vault(db)
        steps.append({
            "step": "export", "status": "ok",
            "detail": f"{len(data['songs'])} songs, {len(data['takes'])} takes",
        })
    except Exception as e:
        steps.append({"step": "export", "status": "error", "detail": str(e)})

    try:
        path = backup_database()
        steps.append({"step": "backup", "status": "ok", "detail": f"Saved to {Path(path).name}"})
    except Exception as e:
        steps.append({"step": "backup", "status": "error", "detail": str(e)})

    return {"steps": steps}


@router.post("/weekly")
def weekly_check(db: Session = Depends(get_db)):
    """Weekly summary: export + backup + headline counts."""
    steps = []

    try:
        data = _export_annotations_to_vault(db)
        steps.append({"step": "export", "status": "ok",
                      "detail": f"{len(data['songs'])} songs exported"})
    except Exception as e:
        steps.append({"step": "export", "status": "error", "detail": str(e)})

    try:
        backup_database()
        backups = list_backups()
        steps.append({"step": "backup", "status": "ok", "detail": f"{len(backups)} backups total"})
    except Exception as e:
        steps.append({"step": "backup", "status": "error", "detail": str(e)})

    counts = {
        "songs": db.query(func.count(Song.id)).scalar(),
        "sessions": db.query(func.count(PracticeSession.id)).scalar(),
        "takes": db.query(func.count(Take.id)).scalar(),
        "audio_files": db.query(func.count(AudioFile.id)).scalar(),
        "rated_takes": db.query(func.count(Take.id)).filter(Take.rating_overall.isnot(None)).scalar(),
        "triage_pending": db.query(func.count(TriageItem.id)).filter(TriageItem.status == "pending").scalar(),
    }
    steps.append({"step": "summary", "status": "ok", "detail": counts})

    return {"steps": steps}
