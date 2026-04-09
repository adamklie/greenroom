from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.recommendations import get_recommendations

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


class RecommendationRead(BaseModel):
    category: str
    priority: str
    title: str
    detail: str
    song_id: int | None = None
    song_title: str | None = None
    data: dict = {}


@router.get("", response_model=list[RecommendationRead])
def list_recommendations(db: Session = Depends(get_db)):
    recs = get_recommendations(db)
    return [RecommendationRead(
        category=r.category,
        priority=r.priority,
        title=r.title,
        detail=r.detail,
        song_id=r.song_id,
        song_title=r.song_title,
        data=r.data,
    ) for r in recs]
