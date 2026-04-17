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
@event.listens_for(Session, "after_commit")
def _schedule_autobackup_on_commit(session: Session) -> None:
    # Lazy import — auto_backup → backup → models → database forms a cycle
    # at module load. Deferring until a commit actually fires means both
    # modules are fully loaded by the time this runs.
    from app.services.auto_backup import schedule_backup
    schedule_backup()
