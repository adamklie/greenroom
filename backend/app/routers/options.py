"""Options API — manage configurable dropdown values."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.option import DEFAULT_OPTIONS, Option

router = APIRouter(prefix="/api/options", tags=["options"])


class OptionRead(BaseModel):
    id: int
    category: str
    value: str
    label: str | None = None
    sort_order: int = 0
    is_default: bool = False
    model_config = {"from_attributes": True}


class OptionCreate(BaseModel):
    category: str
    value: str
    label: str | None = None


@router.get("", response_model=list[OptionRead])
def list_options(category: str | None = Query(None), db: Session = Depends(get_db)):
    """List options, optionally filtered by category."""
    # Seed defaults if table is empty or missing defaults
    existing_count = db.query(Option).filter_by(is_default=True).count()
    if existing_count < len(DEFAULT_OPTIONS):
        for opt in DEFAULT_OPTIONS:
            exists = db.query(Option).filter_by(
                category=opt["category"], value=opt["value"]
            ).first()
            if not exists:
                db.add(Option(**opt, is_default=True))
        db.commit()

    q = db.query(Option)
    if category:
        q = q.filter(Option.category == category)
    return q.order_by(Option.category, Option.sort_order, Option.value).all()


@router.post("", response_model=OptionRead)
def create_option(data: OptionCreate, db: Session = Depends(get_db)):
    """Add a new option value."""
    existing = db.query(Option).filter_by(category=data.category, value=data.value).first()
    if existing:
        return existing

    opt = Option(
        category=data.category,
        value=data.value,
        label=data.label or data.value.replace("_", " ").title(),
        is_default=False,
    )
    db.add(opt)
    db.commit()
    db.refresh(opt)
    return opt


@router.delete("/{option_id}")
def delete_option(option_id: int, db: Session = Depends(get_db)):
    opt = db.query(Option).get(option_id)
    if not opt:
        raise HTTPException(404, "Option not found")
    db.delete(opt)
    db.commit()
    return {"ok": True}
