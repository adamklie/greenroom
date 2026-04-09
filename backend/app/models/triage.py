from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TriageItem(Base):
    __tablename__ = "triage_queue"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_path: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    file_type: Mapped[str | None] = mapped_column(String, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    suggested_song_id: Mapped[int | None] = mapped_column(
        ForeignKey("songs.id"), nullable=True
    )
    suggested_type: Mapped[str | None] = mapped_column(String, nullable=True)
    suggested_source: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
