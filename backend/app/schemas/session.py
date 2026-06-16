from __future__ import annotations

import datetime as _dt
from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.audio_file import AudioFileRead
from app.schemas.take import TakeRead


class SessionCreate(BaseModel):
    name: str | None = None
    date: date
    notes: str | None = None


class SessionUpdate(BaseModel):
    """Partial update — only fields present in the request body are applied
    (use model_dump(exclude_unset=True) to tell 'omitted' from 'set to null').

    NOTE: the date type is referenced as _dt.date, not `date` — a field named
    `date` with a default shadows the imported `date` type during annotation
    evaluation (from __future__ import annotations) and breaks model build."""
    name: str | None = None
    date: _dt.date | None = None
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
