from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.routers import analytics, apple_music, backup, bootstrap_router, content, dashboard, filebrowser, files, gopro, media, recommendations, reorganize, sessions, setlists, songs, sync, tags, trash, triage, upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Auto-backup database on every startup
    try:
        from app.services.backup import backup_database
        if settings.db_path.exists():
            path = backup_database()
            print(f"Auto-backup: {path}")
    except Exception as e:
        print(f"Auto-backup failed (non-fatal): {e}")
    yield


app = FastAPI(title="Greenroom", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(songs.router)
app.include_router(sessions.router)
app.include_router(tags.router)
app.include_router(triage.router)
app.include_router(media.router)
app.include_router(content.router)
app.include_router(setlists.router)
app.include_router(files.router)
app.include_router(recommendations.router)
app.include_router(analytics.router)
app.include_router(apple_music.router)
app.include_router(gopro.router)
app.include_router(filebrowser.router)
app.include_router(upload.router)
app.include_router(backup.router)
app.include_router(sync.router)
app.include_router(reorganize.router)
app.include_router(trash.router)
app.include_router(bootstrap_router.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "greenroom", "version": "0.2.0"}
