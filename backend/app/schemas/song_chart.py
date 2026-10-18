from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SongChartRead(BaseModel):
    id: int
    song_id: int
    file_type: str
    original_filename: str | None = None
    label: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}
