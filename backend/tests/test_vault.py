"""Tests for the VaultBackend protocol and factory selection.

These tests poke at the backend abstraction directly. Filesystem state is
isolated via tmp_path + monkeypatching settings.vault_dir. The `client`
fixture isn't needed here — no HTTP surface.
"""

from __future__ import annotations

import pytest

from app.config import settings
from app.services import vault
from app.services.vault import (
    CloudVaultBackend,
    LocalVaultBackend,
    get_backend,
    ingest_into_vault,
    reset_backend,
    vault_path_for,
)


@pytest.fixture(autouse=True)
def _reset_backend_around_test(monkeypatch, tmp_path):
    """Each test starts with a fresh backend cache and an isolated vault dir."""
    monkeypatch.setattr(settings, "vault_dir", tmp_path / "vault")
    settings.ensure_vault_layout()
    reset_backend()
    yield
    reset_backend()


def test_local_backend_default():
    """With MEDIA_BACKEND unset (default 'local'), get_backend returns Local."""
    assert isinstance(get_backend(), LocalVaultBackend)


def test_local_backend_path_for():
    """path_for returns vault_files_dir / {identifier}.{ext}, lowercased ext."""
    p = vault_path_for("AF12AB34CD", "M4A")
    assert p == settings.vault_files_dir / "AF12AB34CD.m4a"


def test_local_backend_ingest_idempotent(tmp_path):
    """Ingesting the same source twice is a no-op on the second call."""
    src = tmp_path / "source.m4a"
    src.write_bytes(b"hello vault")

    dest1 = ingest_into_vault(src, "AFTEST0001", "m4a")
    assert dest1.exists()
    assert dest1.read_bytes() == b"hello vault"

    # Mutate source — second ingest should NOT overwrite, because the
    # canonical file already exists.
    src.write_bytes(b"changed")
    dest2 = ingest_into_vault(src, "AFTEST0001", "m4a")
    assert dest2 == dest1
    assert dest2.read_bytes() == b"hello vault"


def test_cloud_backend_raises(tmp_path):
    """Every CloudVaultBackend method raises NotImplementedError."""
    backend = CloudVaultBackend()
    with pytest.raises(NotImplementedError, match="R2 backend not yet wired"):
        backend.path_for("AF1", "m4a")
    with pytest.raises(NotImplementedError):
        backend.exists("AF1", "m4a")
    with pytest.raises(NotImplementedError):
        backend.ingest(tmp_path / "x.m4a", "AF1", "m4a")

    # resolve() needs an AudioFile-shaped object; a tiny stand-in is fine
    # because the method raises before touching any attribute.
    class _Stub:
        identifier = "AF1"
        file_type = "m4a"
        file_path = "AF1.m4a"

    with pytest.raises(NotImplementedError):
        backend.resolve(_Stub())


def test_get_backend_respects_setting(monkeypatch):
    """Flipping settings.media_backend to 'r2' surfaces the Cloud stub."""
    monkeypatch.setattr(settings, "media_backend", "r2")
    reset_backend()
    assert isinstance(get_backend(), CloudVaultBackend)

    # And going back to local resumes the on-disk backend.
    monkeypatch.setattr(settings, "media_backend", "local")
    reset_backend()
    assert isinstance(get_backend(), LocalVaultBackend)


def test_get_backend_is_cached():
    """Successive calls return the same instance until reset_backend()."""
    b1 = get_backend()
    b2 = get_backend()
    assert b1 is b2
    reset_backend()
    b3 = get_backend()
    assert b3 is not b1
    # sanity: the module-level _backend is what we just instantiated
    assert vault._backend is b3
