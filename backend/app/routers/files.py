"""File management API: move, consolidate, health check."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.deps import require_editor, require_viewer
from app.database import get_db
from app.services.file_manager import (
    consolidate_all_external,
    consolidate_file,
    health_check,
    move_audio_file,
)
from app.services.vault import CLOUD_UNSUPPORTED_MESSAGE, is_cloud_backend

router = APIRouter(prefix="/api/files", tags=["files"])


class MoveRequest(BaseModel):
    new_path: str


class BrokenLinkRead(BaseModel):
    table: str
    record_id: int
    field: str
    path: str
    song_title: str | None = None


class HealthCheckResponse(BaseModel):
    total_broken: int
    broken_links: list[BrokenLinkRead]


class ConsolidateResponse(BaseModel):
    moved: int
    skipped: int
    errors: list[str]


@router.get("/health", response_model=HealthCheckResponse)
def check_health(db: Session = Depends(get_db), _user=Depends(require_viewer)):
    """Check for broken file links in the database."""
    broken = health_check(db)
    return HealthCheckResponse(
        total_broken=len(broken),
        broken_links=[BrokenLinkRead(
            table=b.table, record_id=b.record_id,
            field=b.field, path=b.path, song_title=b.song_title,
        ) for b in broken],
    )


@router.post("/audio/{audio_file_id}/move", response_model=dict)
def move_file(audio_file_id: int, req: MoveRequest, db: Session = Depends(get_db), _user=Depends(require_editor)):
    """Move an audio file to a new location. Updates DB atomically.

    Cloud mode: not supported — R2 keys are content-addressed, there's no
    user-meaningful "location" to move to.
    """
    if is_cloud_backend():
        raise HTTPException(status_code=501, detail=CLOUD_UNSUPPORTED_MESSAGE)
    try:
        af = move_audio_file(db, audio_file_id, req.new_path)
        return {"ok": True, "new_path": af.file_path}
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(400, str(e))


@router.post("/audio/{audio_file_id}/consolidate", response_model=dict)
def consolidate_one(audio_file_id: int, db: Session = Depends(get_db), _user=Depends(require_editor)):
    """Move a single file from external location into the organized music directory.

    Cloud mode: not supported — every file is already in R2.
    """
    if is_cloud_backend():
        raise HTTPException(status_code=501, detail=CLOUD_UNSUPPORTED_MESSAGE)
    try:
        new_path = consolidate_file(db, audio_file_id)
        return {"ok": True, "new_path": new_path}
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(400, str(e))


@router.post("/consolidate-all", response_model=ConsolidateResponse)
def consolidate_all(db: Session = Depends(get_db), _user=Depends(require_editor)):
    """Move ALL external files into the organized music directory.

    Cloud mode: not supported.
    """
    if is_cloud_backend():
        raise HTTPException(status_code=501, detail=CLOUD_UNSUPPORTED_MESSAGE)
    result = consolidate_all_external(db)
    return ConsolidateResponse(
        moved=result.moved,
        skipped=result.skipped,
        errors=result.errors,
    )
