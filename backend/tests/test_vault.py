"""Tests for the VaultBackend protocol and factory selection.

These tests poke at the backend abstraction directly. Filesystem state is
isolated via tmp_path + monkeypatching settings.vault_dir. The `client`
fixture isn't needed here — no HTTP surface.
"""

from __future__ import annotations

from unittest.mock import MagicMock

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


class _AFStub:
    """Lightweight AudioFile-shaped stand-in for backend tests."""

    identifier = "AFTEST"
    file_type = "m4a"
    file_path = "AFTEST.m4a"


def _patch_boto3(monkeypatch, mock_client: MagicMock) -> MagicMock:
    """Stub out boto3.client so CloudVaultBackend doesn't try to talk to R2."""
    fake_boto3 = MagicMock()
    fake_boto3.client.return_value = mock_client
    monkeypatch.setitem(__import__("sys").modules, "boto3", fake_boto3)
    return fake_boto3


def test_cloud_backend_constructs_with_creds(monkeypatch):
    """CloudVaultBackend wires boto3.client with the configured R2 settings."""
    monkeypatch.setattr(settings, "r2_endpoint_url", "https://acct.r2.cloudflarestorage.com")
    monkeypatch.setattr(settings, "r2_access_key_id", "key-id")
    monkeypatch.setattr(settings, "r2_secret_access_key", "secret")
    monkeypatch.setattr(settings, "r2_bucket", "greenroom-media")

    s3 = MagicMock()
    fake_boto3 = _patch_boto3(monkeypatch, s3)

    backend = CloudVaultBackend()

    fake_boto3.client.assert_called_once()
    args, kwargs = fake_boto3.client.call_args
    assert args == ("s3",)
    assert kwargs["endpoint_url"] == "https://acct.r2.cloudflarestorage.com"
    assert kwargs["aws_access_key_id"] == "key-id"
    assert kwargs["aws_secret_access_key"] == "secret"
    assert kwargs["region_name"] == "auto"
    assert backend._bucket == "greenroom-media"


def test_cloud_backend_ingest_uploads(monkeypatch, tmp_path):
    """ingest() calls s3.upload_file with the canonical key."""
    monkeypatch.setattr(settings, "r2_bucket", "greenroom-media")
    s3 = MagicMock()
    _patch_boto3(monkeypatch, s3)

    src = tmp_path / "foo.m4a"
    src.write_bytes(b"x")

    backend = CloudVaultBackend()
    backend.ingest(src, "AFTEST", "m4a")

    s3.upload_file.assert_called_once_with(str(src), "greenroom-media", "files/AFTEST.m4a")


def test_cloud_backend_url_for_signs(monkeypatch):
    """url_for() generates a presigned GET URL with the configured TTL."""
    monkeypatch.setattr(settings, "r2_bucket", "greenroom-media")
    monkeypatch.setattr(settings, "r2_presign_ttl_seconds", 1800)
    s3 = MagicMock()
    s3.generate_presigned_url.return_value = "https://signed.example/AFTEST.m4a?sig=abc"
    _patch_boto3(monkeypatch, s3)

    backend = CloudVaultBackend()
    url = backend.url_for(_AFStub())

    assert url == "https://signed.example/AFTEST.m4a?sig=abc"
    s3.generate_presigned_url.assert_called_once_with(
        "get_object",
        Params={"Bucket": "greenroom-media", "Key": "files/AFTEST.m4a"},
        ExpiresIn=1800,
    )


def test_cloud_backend_exists_handles_404(monkeypatch):
    """head_object raising ClientError → exists() returns False, not bubble."""
    from botocore.exceptions import ClientError

    monkeypatch.setattr(settings, "r2_bucket", "greenroom-media")
    s3 = MagicMock()
    s3.head_object.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject"
    )
    _patch_boto3(monkeypatch, s3)

    backend = CloudVaultBackend()
    assert backend.exists("AFNOPE", "m4a") is False


def test_local_backend_url_for_returns_none():
    """LocalVaultBackend has no notion of a signed URL — returns None."""
    backend = LocalVaultBackend()
    assert backend.url_for(_AFStub()) is None


def test_get_backend_respects_setting(monkeypatch):
    """Flipping settings.media_backend to 'r2' surfaces CloudVaultBackend."""
    # CloudVaultBackend instantiates boto3 in __init__, which complains about
    # the empty endpoint URL in this test environment — stub the import.
    _patch_boto3(monkeypatch, MagicMock())

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
