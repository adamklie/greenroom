from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SongTabRead(BaseModel):
    id: int
    song_id: int
    label: str | None = None
    instrument: str | None = None
    file_path: str
    file_format: str | None = None
    original_filename: str | None = None
    is_primary: bool = False
    notes: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class SongTabUpdate(BaseModel):
    label: str | None = None
    instrument: str | None = None
    is_primary: bool | None = None
    notes: str | None = None
