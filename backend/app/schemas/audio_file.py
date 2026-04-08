from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class AudioFileRead(BaseModel):
    id: int
    song_id: int | None = None
    file_path: str
    file_type: str | None = None
    source: str | None = None
    version: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
