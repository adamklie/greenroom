from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SongBase(BaseModel):
    title: str
    artist: str | None = None
    project: str
    is_original: bool = False
    status: str = "idea"
    times_practiced: int = 0
    notes: str | None = None


class SongRead(SongBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    has_audio: bool = False
    take_count: int = 0

    model_config = {"from_attributes": True}


class SongUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None


class SongDetail(SongRead):
    takes: list[TakeRead] = []
    audio_files: list[AudioFileRead] = []


# Avoid circular imports
from app.schemas.take import TakeRead  # noqa: E402
from app.schemas.audio_file import AudioFileRead  # noqa: E402

SongDetail.model_rebuild()
