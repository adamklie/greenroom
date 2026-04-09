"""Backup & data protection API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

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
def create_backup():
    """Create a database backup now."""
    path = backup_database()
    return {"ok": True, "path": path}


@router.get("/list")
def get_backups():
    """List available backups."""
    return {"backups": list_backups()}


@router.post("/restore/{filename}")
def restore(filename: str):
    """Restore a backup. Current DB is backed up first."""
    try:
        path = restore_backup(filename)
        return {"ok": True, "restored_from": path}
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.post("/hash-files")
def hash_files(db: Session = Depends(get_db)):
    """Compute SHA256 hashes for all audio files (for auto-heal)."""
    stats = hash_all_files(db)
    return stats


@router.post("/auto-heal")
def heal(db: Session = Depends(get_db)):
    """Find broken file paths and fix them using content hashes."""
    stats = auto_heal_paths(db)
    return stats


@router.post("/export")
def export(db: Session = Depends(get_db)):
    """Export all annotations as JSON."""
    result = export_annotations(db)
    return {"ok": True, "path": result["path"],
            "songs": len(result["data"]["songs"]),
            "takes": len(result["data"]["takes"]),
            "setlists": len(result["data"]["setlists"])}
