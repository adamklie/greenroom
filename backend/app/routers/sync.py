"""Sync & maintenance API — combines backup, hash, export, health check into workflows."""

import subprocess
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import AudioFile, PracticeSession, Song, Take, TriageItem
from app.services.backup import (
    backup_database,
    export_annotations,
    hash_all_files,
    list_backups,
)
from app.services.bootstrap import run_bootstrap
from app.services.file_manager import health_check

router = APIRouter(prefix="/api/sync", tags=["sync"])


@router.post("/after-practice")
def after_practice(db: Session = Depends(get_db)):
    """One-click post-practice routine: rescan → hash → export → backup."""
    steps = []

    # 1. Rescan filesystem
    try:
        run_bootstrap()
        steps.append({"step": "rescan", "status": "ok", "detail": "Filesystem rescanned"})
    except Exception as e:
        steps.append({"step": "rescan", "status": "error", "detail": str(e)})

    # 2. Hash new files
    try:
        hash_stats = hash_all_files(db)
        steps.append({"step": "hash", "status": "ok",
                      "detail": f"{hash_stats['newly_hashed']} new, {hash_stats['already_hashed']} cached"})
    except Exception as e:
        steps.append({"step": "hash", "status": "error", "detail": str(e)})

    # 3. Export annotations
    try:
        import json
        result = export_annotations(db)
        export_dir = Path(settings.music_dir) / "greenroom" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        (export_dir / "annotations_latest.json").write_text(
            json.dumps(result["data"], indent=2)
        )
        steps.append({"step": "export", "status": "ok",
                      "detail": f"{len(result['data']['songs'])} songs, {len(result['data']['takes'])} takes"})
    except Exception as e:
        steps.append({"step": "export", "status": "error", "detail": str(e)})

    # 4. Backup database
    try:
        path = backup_database()
        steps.append({"step": "backup", "status": "ok", "detail": f"Saved to {Path(path).name}"})
    except Exception as e:
        steps.append({"step": "backup", "status": "error", "detail": str(e)})

    # 5. Git commit (if in a git repo)
    try:
        greenroom_dir = settings.music_dir / "greenroom"
        result = subprocess.run(
            ["git", "add", "exports/annotations_latest.json"],
            cwd=str(greenroom_dir), capture_output=True, text=True, timeout=10,
        )
        diff = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(greenroom_dir), capture_output=True, timeout=10,
        )
        if diff.returncode != 0:  # There are staged changes
            date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
            subprocess.run(
                ["git", "commit", "-m", f"post-practice: update annotations {date_str}"],
                cwd=str(greenroom_dir), capture_output=True, text=True, timeout=10,
            )
            steps.append({"step": "git_commit", "status": "ok", "detail": "Annotations committed"})
        else:
            steps.append({"step": "git_commit", "status": "ok", "detail": "No changes to commit"})
    except Exception as e:
        steps.append({"step": "git_commit", "status": "skipped", "detail": str(e)})

    return {"steps": steps}


@router.post("/weekly")
def weekly_check(db: Session = Depends(get_db)):
    """One-click weekly health check."""
    steps = []

    # 1. Rescan
    try:
        run_bootstrap()
        steps.append({"step": "rescan", "status": "ok", "detail": "Filesystem rescanned"})
    except Exception as e:
        steps.append({"step": "rescan", "status": "error", "detail": str(e)})

    # 2. File health
    try:
        broken = health_check(db)
        if broken:
            steps.append({"step": "health", "status": "warning",
                          "detail": f"{len(broken)} broken file links"})
        else:
            steps.append({"step": "health", "status": "ok", "detail": "All file links healthy"})
    except Exception as e:
        steps.append({"step": "health", "status": "error", "detail": str(e)})

    # 3. Hash
    try:
        stats = hash_all_files(db)
        detail = f"{stats['already_hashed'] + stats['newly_hashed']} files hashed"
        if stats['missing_files'] > 0:
            detail += f", {stats['missing_files']} missing"
        steps.append({"step": "hash", "status": "ok", "detail": detail})
    except Exception as e:
        steps.append({"step": "hash", "status": "error", "detail": str(e)})

    # 4. Export
    try:
        import json
        result = export_annotations(db)
        export_dir = Path(settings.music_dir) / "greenroom" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        (export_dir / "annotations_latest.json").write_text(
            json.dumps(result["data"], indent=2)
        )
        steps.append({"step": "export", "status": "ok",
                      "detail": f"{len(result['data']['songs'])} songs exported"})
    except Exception as e:
        steps.append({"step": "export", "status": "error", "detail": str(e)})

    # 5. Backup
    try:
        backup_database()
        backups = list_backups()
        steps.append({"step": "backup", "status": "ok", "detail": f"{len(backups)} backups total"})
    except Exception as e:
        steps.append({"step": "backup", "status": "error", "detail": str(e)})

    # 6. Summary stats
    stats = {
        "songs": db.query(func.count(Song.id)).scalar(),
        "sessions": db.query(func.count(PracticeSession.id)).scalar(),
        "takes": db.query(func.count(Take.id)).scalar(),
        "audio_files": db.query(func.count(AudioFile.id)).scalar(),
        "rated_takes": db.query(func.count(Take.id)).filter(Take.rating_overall.isnot(None)).scalar(),
        "triage_pending": db.query(func.count(TriageItem.id)).filter(TriageItem.status == "pending").scalar(),
    }
    steps.append({"step": "summary", "status": "ok", "detail": stats})

    # 7. Git commit
    try:
        greenroom_dir = settings.music_dir / "greenroom"
        subprocess.run(["git", "add", "exports/annotations_latest.json"],
                      cwd=str(greenroom_dir), capture_output=True, timeout=10)
        diff = subprocess.run(["git", "diff", "--cached", "--quiet"],
                            cwd=str(greenroom_dir), capture_output=True, timeout=10)
        if diff.returncode != 0:
            date_str = datetime.now().strftime("%Y-%m-%d")
            subprocess.run(
                ["git", "commit", "-m", f"weekly: update annotations {date_str}"],
                cwd=str(greenroom_dir), capture_output=True, text=True, timeout=10,
            )
            steps.append({"step": "git_commit", "status": "ok", "detail": "Committed"})
        else:
            steps.append({"step": "git_commit", "status": "ok", "detail": "No changes"})

        # Check unpushed
        unpushed = subprocess.run(
            ["git", "log", "origin/main..HEAD", "--oneline"],
            cwd=str(greenroom_dir), capture_output=True, text=True, timeout=10,
        )
        count = len([l for l in unpushed.stdout.strip().split("\n") if l])
        if count > 0:
            steps.append({"step": "git_push", "status": "warning",
                          "detail": f"{count} unpushed commits"})
    except Exception as e:
        steps.append({"step": "git_commit", "status": "skipped", "detail": str(e)})

    return {"steps": steps}


@router.post("/git-push")
def git_push():
    """Push local commits to remote."""
    try:
        greenroom_dir = settings.music_dir / "greenroom"
        result = subprocess.run(
            ["git", "push"],
            cwd=str(greenroom_dir), capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return {"ok": True, "detail": "Pushed to remote"}
        else:
            return {"ok": False, "detail": result.stderr}
    except Exception as e:
        return {"ok": False, "detail": str(e)}
