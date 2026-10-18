"""Charts (PDF / image) attached to songs.

Files live in the vault next to recordings ({identifier}.{ext}, local disk or
R2). They're small, so the backend serves the bytes itself rather than
redirecting to a presigned R2 URL: same-origin keeps pdf.js happy (no CORS)
and lets us set an inline Content-Type, which R2 objects don't carry.
"""

import hashlib
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.deps import project_editor, project_viewer
from app.database import get_db
from app.models import Song, SongChart
from app.schemas.song_chart import SongChartRead
from app.services.vault import get_backend, ingest_into_vault

router = APIRouter(prefix="/api/charts", tags=["charts"])

CHART_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
}
MAX_CHART_BYTES = 20 * 1024 * 1024


def _new_identifier(filename: str) -> str:
    raw = f"{filename}:{datetime.now().isoformat()}"
    return "CH" + hashlib.sha256(raw.encode()).hexdigest()[:8].upper()


@router.get("", response_model=list[SongChartRead])
def list_charts(song_id: int = Query(...), db: Session = Depends(get_db), _user=Depends(project_viewer)):
    return db.query(SongChart).filter(SongChart.song_id == song_id).order_by(SongChart.id).all()


@router.post("", response_model=SongChartRead)
async def upload_chart(
    file: UploadFile = File(...),
    song_id: int = Form(...),
    label: str | None = Form(None),
    db: Session = Depends(get_db),
    _user=Depends(project_editor),
):
    # Scoped lookup: can't attach a chart to another project's song.
    if db.query(Song).filter(Song.id == song_id).first() is None:
        raise HTTPException(404, "Song not found")
    filename = Path(file.filename or "").name
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in CHART_TYPES:
        raise HTTPException(400, f"Unsupported chart format. Use: {', '.join(sorted(CHART_TYPES))}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tf:
        shutil.copyfileobj(file.file, tf)
        staged = Path(tf.name)
    try:
        if staged.stat().st_size > MAX_CHART_BYTES:
            raise HTTPException(413, "Chart files must be under 20 MB")
        identifier = _new_identifier(filename)
        ingest_into_vault(staged, identifier, ext)
    finally:
        staged.unlink(missing_ok=True)

    chart = SongChart(
        song_id=song_id, identifier=identifier, file_type=ext,
        original_filename=filename, label=label or None,
    )
    db.add(chart)
    db.commit()
    db.refresh(chart)
    return chart


@router.get("/{chart_id}/file")
def serve_chart(chart_id: int, db: Session = Depends(get_db), _user=Depends(project_viewer)):
    chart = db.query(SongChart).filter(SongChart.id == chart_id).first()
    if not chart:
        raise HTTPException(404, "Chart not found")
    try:
        data = get_backend().read_bytes(chart.identifier, chart.file_type)
    except FileNotFoundError:
        raise HTTPException(404, "Chart file missing from the vault")
    return Response(
        data,
        media_type=CHART_TYPES.get(chart.file_type, "application/octet-stream"),
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.delete("/{chart_id}")
def delete_chart(chart_id: int, db: Session = Depends(get_db), _user=Depends(project_editor)):
    """Removes the chart from its song. The stored file is left in the vault,
    matching how recordings are handled."""
    chart = db.query(SongChart).filter(SongChart.id == chart_id).first()
    if not chart:
        raise HTTPException(404, "Chart not found")
    db.delete(chart)
    db.commit()
    return {"ok": True}
