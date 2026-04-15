"""Guitar Pro tab upload, listing, and serving."""

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import Song, SongTab
from app.schemas.song_tab import SongTabRead, SongTabUpdate

router = APIRouter(prefix="/api/tabs", tags=["tabs"])

TAB_EXTENSIONS = {".gp", ".gp3", ".gp4", ".gp5", ".gpx", ".gp7"}


def _resolve_tab_path(file_path: str) -> Path:
    p = Path(file_path)
    if p.is_absolute():
        return p
    return settings.music_dir / file_path


@router.get("", response_model=list[SongTabRead])
def list_tabs(song_id: int | None = Query(None), db: Session = Depends(get_db)):
    q = db.query(SongTab)
    if song_id is not None:
        q = q.filter(SongTab.song_id == song_id)
    return q.order_by(SongTab.is_primary.desc(), SongTab.created_at.desc()).all()


@router.get("/{tab_id}", response_model=SongTabRead)
def get_tab(tab_id: int, db: Session = Depends(get_db)):
    tab = db.query(SongTab).get(tab_id)
    if not tab:
        raise HTTPException(404, "Tab not found")
    return tab


@router.get("/{tab_id}/file")
def serve_tab_file(tab_id: int, db: Session = Depends(get_db)):
    """Serve the raw .gp/.gp5/.gpx file for AlphaTab to parse."""
    tab = db.query(SongTab).get(tab_id)
    if not tab:
        raise HTTPException(404, "Tab not found")
    full = _resolve_tab_path(tab.file_path)
    if not full.exists():
        raise HTTPException(404, f"File missing on disk: {tab.file_path}")
    return FileResponse(
        str(full),
        media_type="application/octet-stream",
        filename=tab.original_filename or full.name,
    )


@router.post("", response_model=SongTabRead)
async def upload_tab(
    file: UploadFile = File(...),
    song_id: int = Form(...),
    label: str | None = Form(None),
    instrument: str | None = Form("guitar"),
    is_primary: bool = Form(False),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
):
    """Upload a Guitar Pro tab file and link it to a song."""
    if not file.filename:
        raise HTTPException(400, "No filename")

    song = db.query(Song).get(song_id)
    if not song:
        raise HTTPException(404, f"Song {song_id} not found")

    ext = Path(file.filename).suffix.lower()
    if ext not in TAB_EXTENSIONS:
        raise HTTPException(400, f"Unsupported format {ext}. Use: {', '.join(sorted(TAB_EXTENSIONS))}")

    # Organize under music_dir/tabs/{song_id}/
    tabs_dir = settings.music_dir / "tabs" / str(song_id)
    tabs_dir.mkdir(parents=True, exist_ok=True)

    dest = tabs_dir / file.filename
    # Handle collision
    if dest.exists():
        stem, suffix = dest.stem, dest.suffix
        counter = 1
        while dest.exists():
            dest = tabs_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    rel_path = str(dest.relative_to(settings.music_dir))

    # If setting as primary, unset others
    if is_primary:
        db.query(SongTab).filter(SongTab.song_id == song_id).update({"is_primary": False})

    tab = SongTab(
        song_id=song_id,
        label=label,
        instrument=instrument,
        file_path=rel_path,
        file_format=ext.lstrip("."),
        original_filename=file.filename,
        is_primary=is_primary,
        notes=notes,
    )
    db.add(tab)
    db.commit()
    db.refresh(tab)
    return tab


@router.patch("/{tab_id}", response_model=SongTabRead)
def update_tab(tab_id: int, data: SongTabUpdate, db: Session = Depends(get_db)):
    tab = db.query(SongTab).get(tab_id)
    if not tab:
        raise HTTPException(404, "Tab not found")

    changes = data.model_dump(exclude_unset=True)
    # If setting primary, unset others in same song
    if changes.get("is_primary") is True:
        db.query(SongTab).filter(
            SongTab.song_id == tab.song_id, SongTab.id != tab_id
        ).update({"is_primary": False})

    for field, value in changes.items():
        setattr(tab, field, value)
    db.commit()
    db.refresh(tab)
    return tab


@router.delete("/{tab_id}")
def delete_tab(tab_id: int, db: Session = Depends(get_db)):
    tab = db.query(SongTab).get(tab_id)
    if not tab:
        raise HTTPException(404, "Tab not found")

    full = _resolve_tab_path(tab.file_path)
    if full.exists():
        # Soft delete to _trash
        trash_dir = settings.music_dir / "_trash" / "tabs"
        trash_dir.mkdir(parents=True, exist_ok=True)
        trash_path = trash_dir / full.name
        if trash_path.exists():
            stem, suffix = trash_path.stem, trash_path.suffix
            counter = 1
            while trash_path.exists():
                trash_path = trash_dir / f"{stem}_{counter}{suffix}"
                counter += 1
        shutil.move(str(full), str(trash_path))

    db.delete(tab)
    db.commit()
    return {"ok": True, "id": tab_id}
