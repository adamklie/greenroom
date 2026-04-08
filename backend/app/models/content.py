from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ContentPost(Base):
    __tablename__ = "content_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    song_id: Mapped[int | None] = mapped_column(ForeignKey("songs.id"), nullable=True)
    take_id: Mapped[int | None] = mapped_column(ForeignKey("takes.id"), nullable=True)
    audio_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("audio_files.id"), nullable=True
    )
    platform: Mapped[str | None] = mapped_column(String, nullable=True)
    post_type: Mapped[str | None] = mapped_column(String, nullable=True)
    scheduled_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String, default="planned")
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
