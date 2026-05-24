"""Backup & data protection API."""

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.deps import require_editor, require_viewer
from app.database import get_db
from app.services.backup import (
    auto_heal_paths,
    backup_database,
    export_annotations,
    hash_all_files,
    list_backups,
    restore_backup,
)

router = APIRouter(prefix="/api/backup", tags=["backup"])


@router.post("/create")
def create_backup(_user=Depends(require_editor)):
    """Create a database backup now."""
    path = backup_database()
    return {"ok": True, "path": path}


@router.get("/list")
def get_backups(_user=Depends(require_viewer)):
    """List available backups."""
    return {"backups": list_backups()}


@router.post("/restore/{filename}")
def restore(filename: str, _user=Depends(require_editor)):
    """Restore a backup. Current DB is backed up first."""
    try:
        path = restore_backup(filename)
        return {"ok": True, "restored_from": path}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.post("/hash-files")
def hash_files(db: Session = Depends(get_db), _user=Depends(require_editor)):
    """Compute SHA256 hashes for all audio files (for auto-heal)."""
    stats = hash_all_files(db)
    return stats


@router.post("/auto-heal")
def heal(db: Session = Depends(get_db), _user=Depends(require_editor)):
    """Find broken file paths and fix them using content hashes."""
    stats = auto_heal_paths(db)
    return stats


@router.post("/export")
def export(db: Session = Depends(get_db), _user=Depends(require_editor)):
    """Export all annotations as JSON (writes a server-side file and returns metadata)."""
    result = export_annotations(db)
    return {"ok": True, "path": result["path"],
            "songs": len(result["data"]["songs"]),
            "takes": len(result["data"]["takes"]),
            "setlists": len(result["data"]["setlists"])}


@router.get("/export-download")
def export_download(db: Session = Depends(get_db), _user=Depends(require_editor)):
    """Stream all annotations as a downloadable JSON attachment.

    The POST /export sibling writes to the server's vault dir; this one
    streams directly to the browser so editors can grab a portable copy
    without an SSH session.
    """
    result = export_annotations(db)
    content = json.dumps(result["data"], indent=2, default=str)
    filename = f"greenroom-export-{datetime.utcnow().strftime('%Y-%m-%d')}.json"
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
