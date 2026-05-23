import os
from contextlib import asynccontextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.auth.router import router as auth_router
from app.routers import analytics, audio_files, backup, dashboard, feedback, filebrowser, files, gopro, media, options, sessions, setlists, songs, tabs as tabs_router, tags, trash, trim, upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Apply pending Alembic migrations on startup. For first-time setup on
    # a brand-new DB this creates every table. For an existing DB that was
    # initially built by Base.metadata.create_all (pre-Alembic), run
    # `python scripts/stamp_baseline.py` once to mark it as already-at-head
    # — otherwise this would try to re-create existing tables and fail.
    alembic_ini = Path(__file__).resolve().parent.parent / "alembic.ini"
    cfg = Config(str(alembic_ini))
    command.upgrade(cfg, "head")
    # Auto-backup runs in a background thread so startup isn't blocked.
    # On iCloud-backed filesystems the DB copy can take seconds; doing it
    # synchronously slows every reload.
    try:
        import threading
        from app.services.backup import backup_database
        if settings.db_path.exists():
            def _bg():
                try:
                    path = backup_database()
                    print(f"Auto-backup: {path}")
                except Exception as e:
                    print(f"Auto-backup failed (non-fatal): {e}")
            threading.Thread(target=_bg, daemon=True).start()
    except Exception as e:
        print(f"Auto-backup scheduling failed: {e}")
    yield


app = FastAPI(title="Greenroom", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dashboard.router)
app.include_router(songs.router)
app.include_router(audio_files.router)
app.include_router(sessions.router)
app.include_router(tags.router)
app.include_router(media.router)
app.include_router(setlists.router)
app.include_router(files.router)
app.include_router(analytics.router)
app.include_router(gopro.router)
app.include_router(filebrowser.router)
app.include_router(upload.router)
app.include_router(backup.router)
app.include_router(trash.router)
app.include_router(options.router)
app.include_router(feedback.router)
app.include_router(trim.router)
app.include_router(tabs_router.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "greenroom", "version": "0.2.0"}


# Serve the built React SPA from `/` when a static directory is configured.
# Mounted last so every `/api/*` route above takes priority. `html=True`
# makes unknown sub-paths (e.g. /sessions, /library) fall back to index.html
# so client-side routing works on hard refresh. When `static_dir` is empty
# or missing (local dev where Vite serves the frontend separately), we skip
# the mount entirely.
_static_dir = settings.static_dir
if _static_dir and os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")
