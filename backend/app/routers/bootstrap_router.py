from fastapi import APIRouter

from app.services.bootstrap import run_bootstrap

router = APIRouter(prefix="/api/bootstrap", tags=["bootstrap"])


@router.post("/scan")
def rescan():
    """Re-scan the filesystem and update the database."""
    run_bootstrap()
    return {"ok": True, "message": "Bootstrap complete"}
