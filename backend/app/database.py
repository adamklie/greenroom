from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Debounced DB backup on every commit. Installed unconditionally so the vault
# gets a rolling snapshot after any annotation change; a burst of writes
# collapses to a single backup via schedule_backup's debounce.
from app.services.auto_backup import schedule_backup  # noqa: E402


@event.listens_for(Session, "after_commit")
def _schedule_autobackup_on_commit(session: Session) -> None:
    # Only backup on sessions that actually wrote something. SQLAlchemy's
    # `session.new | session.dirty | session.deleted` are empty inside
    # after_commit, but the flag `session.info` isn't — simplest is to
    # always schedule and let the debounce collapse no-op commits.
    schedule_backup()
