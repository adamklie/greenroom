from sqlalchemy import Column, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# Junction tables
song_tags = Table(
    "song_tags",
    Base.metadata,
    Column("song_id", Integer, ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)

take_tags = Table(
    "take_tags",
    Base.metadata,
    Column("take_id", Integer, ForeignKey("takes.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String, nullable=False, default="general")
    color: Mapped[str | None] = mapped_column(String, nullable=True)
    is_predefined: Mapped[bool] = mapped_column(Integer, nullable=False, default=True)

    songs: Mapped[list["Song"]] = relationship(  # noqa: F821
        secondary=song_tags, back_populates="tags"
    )
    takes: Mapped[list["Take"]] = relationship(  # noqa: F821
        secondary=take_tags, back_populates="tags"
    )


# Predefined tags to seed on first boot
PREDEFINED_TAGS = [
    {"name": "needs-work", "category": "take"},
    {"name": "good-take", "category": "take"},
    {"name": "false-start", "category": "take"},
    {"name": "best-take", "category": "take"},
    {"name": "demo", "category": "general"},
    {"name": "final-mix", "category": "general"},
    {"name": "live-ready", "category": "song"},
    {"name": "needs-lyrics", "category": "song"},
    {"name": "needs-arrangement", "category": "song"},
    {"name": "crowd-pleaser", "category": "song"},
    {"name": "setlist-candidate", "category": "song"},
    {"name": "archived", "category": "general"},
]
