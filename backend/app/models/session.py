from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PracticeSession(Base):
    # Table is "sessions" (the API and UI call these "sessions"); the Python
    # class stays PracticeSession to avoid colliding with sqlalchemy.orm.Session.
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    # Optional user-provided session title; UI falls back to the date when null.
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    project: Mapped[str] = mapped_column(String, nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    folder_path: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    takes: Mapped[list["Take"]] = relationship(back_populates="session")  # noqa: F821
