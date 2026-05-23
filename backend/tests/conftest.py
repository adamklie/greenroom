"""Shared pytest fixtures for greenroom backend tests.

Everything that touches the filesystem or the live DB is isolated per-test:
- `db` builds an in-memory SQLite with the full schema applied.
- `client` monkeypatches `settings` so the app uses `tmp_path` for the vault,
  the legacy music dir, and a throwaway DB path (so lifespan's auto-backup
  doesn't touch the real DB).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app


@pytest.fixture
def db():
    """Fresh in-memory SQLite session with full schema. One DB per test."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def client(db, tmp_path, monkeypatch):
    """TestClient against the real app with isolated filesystem + DB.

    Points settings at tmp_path for the vault and legacy music_dir, and
    swaps a non-existent db_path so the lifespan auto-backup short-circuits.
    `get_db` is overridden to yield the in-memory `db` session.
    """
    monkeypatch.setattr(settings, "music_dir", tmp_path)
    monkeypatch.setattr(settings, "vault_dir", tmp_path / "vault")
    monkeypatch.setattr(settings, "db_path", tmp_path / "test.db")
    settings.ensure_vault_layout()

    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_audio_file_path() -> Path:
    """Path to the 1-second 440Hz sine wave used for upload tests."""
    return Path(__file__).parent / "fixtures" / "sample.m4a"
