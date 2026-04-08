from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.routers import bootstrap_router, content, dashboard, media, repertoire, sessions, setlists


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Greenroom", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(repertoire.router)
app.include_router(sessions.router)
app.include_router(media.router)
app.include_router(content.router)
app.include_router(setlists.router)
app.include_router(bootstrap_router.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "greenroom"}
