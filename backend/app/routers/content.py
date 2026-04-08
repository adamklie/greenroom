from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ContentPost, Song
from app.schemas.content import ContentPostCreate, ContentPostRead, ContentPostUpdate

router = APIRouter(prefix="/api/content", tags=["content"])


def _post_to_read(post: ContentPost, db: Session) -> ContentPostRead:
    song_title = None
    if post.song_id:
        song = db.query(Song).get(post.song_id)
        if song:
            song_title = song.title

    return ContentPostRead(
        id=post.id,
        title=post.title,
        song_id=post.song_id,
        take_id=post.take_id,
        audio_file_id=post.audio_file_id,
        platform=post.platform,
        post_type=post.post_type,
        scheduled_date=post.scheduled_date,
        status=post.status,
        caption=post.caption,
        notes=post.notes,
        created_at=post.created_at,
        updated_at=post.updated_at,
        song_title=song_title,
    )


@router.get("/posts", response_model=list[ContentPostRead])
def list_posts(
    status: str | None = Query(None),
    platform: str | None = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(ContentPost)
    if status:
        q = q.filter(ContentPost.status == status)
    if platform:
        q = q.filter(ContentPost.platform == platform)

    posts = q.order_by(ContentPost.scheduled_date.asc().nullslast()).all()
    return [_post_to_read(p, db) for p in posts]


@router.post("/posts", response_model=ContentPostRead)
def create_post(data: ContentPostCreate, db: Session = Depends(get_db)):
    post = ContentPost(**data.model_dump())
    db.add(post)
    db.commit()
    db.refresh(post)
    return _post_to_read(post, db)


@router.patch("/posts/{post_id}", response_model=ContentPostRead)
def update_post(post_id: int, data: ContentPostUpdate, db: Session = Depends(get_db)):
    post = db.query(ContentPost).get(post_id)
    if not post:
        raise HTTPException(404, "Post not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(post, field, value)
    post.updated_at = datetime.now()

    db.commit()
    db.refresh(post)
    return _post_to_read(post, db)


@router.delete("/posts/{post_id}")
def delete_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(ContentPost).get(post_id)
    if not post:
        raise HTTPException(404, "Post not found")
    db.delete(post)
    db.commit()
    return {"ok": True}
