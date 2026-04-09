from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Tag
from app.schemas.tag import TagCreate, TagRead

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagRead])
def list_tags(
    category: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Tag)
    if category:
        q = q.filter(Tag.category == category)
    return q.order_by(Tag.category, Tag.name).all()


@router.post("", response_model=TagRead)
def create_tag(data: TagCreate, db: Session = Depends(get_db)):
    tag = Tag(name=data.name, category=data.category, color=data.color, is_predefined=False)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag
