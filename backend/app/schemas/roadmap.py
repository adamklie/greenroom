from __future__ import annotations

from pydantic import BaseModel


class RoadmapTaskRead(BaseModel):
    id: int
    phase: int
    phase_title: str | None = None
    category: str | None = None
    task_text: str
    completed: bool = False
    sort_order: int = 0

    model_config = {"from_attributes": True}


class RoadmapTaskUpdate(BaseModel):
    completed: bool


class RoadmapPhase(BaseModel):
    phase: int
    phase_title: str
    tasks: list[RoadmapTaskRead]
    total: int
    completed: int
