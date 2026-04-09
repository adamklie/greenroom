"""Server-side file browser — lets the frontend navigate the local filesystem."""

from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/browse", tags=["filebrowser"])

VIDEO_EXTS = {".mp4", ".MP4", ".mov", ".MOV"}


@router.get("")
def browse_directory(path: str = Query(default="~")):
    """List contents of a directory. Returns folders and video files."""
    dir_path = Path(path).expanduser().resolve()

    if not dir_path.exists() or not dir_path.is_dir():
        return {"path": str(dir_path), "parent": str(dir_path.parent), "entries": [], "error": "Directory not found"}

    entries = []
    try:
        for item in sorted(dir_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            # Skip hidden files
            if item.name.startswith("."):
                continue
            if item.is_dir():
                entries.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "directory",
                })
            elif item.suffix in VIDEO_EXTS:
                size_mb = round(item.stat().st_size / (1024 * 1024), 1)
                entries.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "video",
                    "size_mb": size_mb,
                })
    except PermissionError:
        return {"path": str(dir_path), "parent": str(dir_path.parent), "entries": [], "error": "Permission denied"}

    return {
        "path": str(dir_path),
        "parent": str(dir_path.parent),
        "entries": entries,
    }
