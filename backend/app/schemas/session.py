from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.take import TakeRead


class SessionRead(BaseModel):
    id: int
    date: date
    project: str
    folder_path: str
    notes: str | None = None
    created_at: datetime | None = None
    take_count: int = 0

    model_config = {"from_attributes": True}


class SessionDetail(SessionRead):
    takes: list[TakeRead] = []
