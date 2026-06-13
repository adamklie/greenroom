from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker, with_loader_criteria

from app.config import settings
from app.scoping import get_scope

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


def _scoped_models():
    # Lazy import — models import this module (Base), so importing them at load
    # time would cycle. Only the content tables that carry project_id; the
    # access-control tables (Project, ProjectMember, User) stay unscoped so the
    # membership lookup that *determines* the scope isn't itself filtered.
    from app.models import AudioFile, PracticeSession, Setlist, Song, Take
    return (AudioFile, PracticeSession, Setlist, Song, Take)


@event.listens_for(Session, "do_orm_execute")
def _apply_project_scope(execute_state) -> None:
    """Restrict every ORM SELECT to the request's accessible projects.

    Inert unless the multi_project flag is on AND a scope is set. Applied to
    every SELECT — including relationship/lazy loads — so it fails closed: a
    lazy `song.audio_files` load is filtered just like a top-level query. Only
    column loads are skipped (nothing to filter). A cross-project row simply
    isn't returned (→ existing 404 path). include_aliases=True covers eager
    joins. (We deliberately do NOT skip relationship loads: with plain
    with_loader_criteria they would otherwise leak through lazy loads.)
    """
    if not settings.multi_project:
        return
    if not execute_state.is_select or execute_state.is_column_load:
        return
    scope = get_scope()
    if scope is None:
        return  # unscoped: admin / system / dev-bypass
    ids = list(scope)
    for model in _scoped_models():
        execute_state.statement = execute_state.statement.options(
            with_loader_criteria(model, model.project_id.in_(ids), include_aliases=True)
        )


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
