from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Take(Base):
    __tablename__ = "takes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("practice_sessions.id"))
    song_id: Mapped[int | None] = mapped_column(ForeignKey("songs.id"), nullable=True)
    clip_name: Mapped[str] = mapped_column(String, nullable=False)
    source_video: Mapped[str | None] = mapped_column(String, nullable=True)
    start_time: Mapped[str | None] = mapped_column(String, nullable=True)
    end_time: Mapped[str | None] = mapped_column(String, nullable=True)
    video_path: Mapped[str | None] = mapped_column(String, nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String, nullable=True)

    # Multi-dimensional ratings (all 1-5, nullable)
    rating_overall: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_vocals: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_guitar: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_drums: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_tone: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_timing: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rating_energy: Mapped[int | None] = mapped_column(Integer, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    session: Mapped["PracticeSession"] = relationship(back_populates="takes")  # noqa: F821
    song: Mapped["Song | None"] = relationship(back_populates="takes")  # noqa: F821
    tags: Mapped[list["Tag"]] = relationship(  # noqa: F821
        secondary="take_tags", back_populates="takes"
    )
