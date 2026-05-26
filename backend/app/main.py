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


# Serve the built React SPA when a static directory is configured.
#
# StaticFiles(html=True) only handles directory-style requests — it does NOT
# fall back to index.html for arbitrary SPA paths like /library or /sessions.
# So we use a two-piece setup:
#   1. /assets/* mount serves the hashed Vite bundle directly (correct MIME
#      types, conditional GETs, all that)
#   2. A catch-all GET serves real files in static_dir if they exist
#      (favicon.ico, robots.txt, etc.), otherwise returns index.html so
#      client-side routing takes over.
#
# Registration order matters: every /api/* router above is registered before
# this catch-all, so API routes take priority. The catch-all is only reached
# for paths the API didn't claim.
_static_dir = settings.static_dir
if _static_dir and os.path.isdir(_static_dir):
    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    _assets_dir = os.path.join(_static_dir, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/{full_path:path}")
    def spa_catchall(full_path: str):
        """Serve a real file if it exists in static_dir, otherwise the SPA shell."""
        # Don't intercept /api or /assets (those are handled above)
        if full_path.startswith("api/") or full_path.startswith("assets/"):
            raise HTTPException(404)
        candidate = os.path.join(_static_dir, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_static_dir, "index.html"))
