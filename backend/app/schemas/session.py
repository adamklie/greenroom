from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.audio_file import AudioFileRead
from app.schemas.take import TakeRead


class SessionCreate(BaseModel):
    name: str | None = None
    date: date
    notes: str | None = None


class SessionRead(BaseModel):
    id: int
    name: str | None = None
    date: date
    project: str
    folder_path: str
    notes: str | None = None
    created_at: datetime | None = None
    track_count: int = 0

    model_config = {"from_attributes": True}


class SessionDetail(SessionRead):
    takes: list[TakeRead] = []
    audio_files: list[AudioFileRead] = []
