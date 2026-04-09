from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import apple_music, bootstrap_router, content, dashboard, files, media, recommendations, sessions, setlists, songs, tags, triage


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
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
app.include_router(apple_music.router)
app.include_router(bootstrap_router.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "greenroom", "version": "0.2.0"}
