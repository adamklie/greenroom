"""Vault: canonical flat storage for imported media.

Every AudioFile has a stable identifier (e.g. AF12AB34CD). The vault stores
the file at `vault_dir/files/{identifier}.{ext}`. That's it — no nested
folders, no project-based organization. Human browsability is traded for
a path that's fully derivable from DB metadata, so restoring the DB from a
backup is sufficient to regain access to every file.

Source files on the user's local disk are left alone after import; the
vault copy is the canonical reference.

## Backend abstraction

Storage is routed through a `VaultBackend` protocol. The default
`LocalVaultBackend` writes to the iCloud vault on disk; `CloudVaultBackend`
is a stub for future Cloudflare R2 hosting (not yet wired). Selection is
driven by `settings.media_backend` ("local" | "r2"). The public functions
(`vault_path_for`, `resolve_audio_path`, `ingest_into_vault`) are thin
wrappers over the active backend, so existing callers don't change.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Protocol

from app.config import settings
from app.models import AudioFile


class VaultBackend(Protocol):
    """Pluggable storage backend for vault media."""

    def path_for(self, identifier: str, file_type: str) -> Path:
        """Return the canonical location for `{identifier}.{ext}`."""
        ...

    def resolve(self, af: AudioFile) -> Path:
        """Locate an AudioFile, preferring the canonical path."""
        ...

    def ingest(self, source: Path, identifier: str, file_type: str) -> Path:
        """Copy/upload `source` into the vault. Returns the canonical path.
        Idempotent: re-ingesting the same identifier is a no-op."""
        ...

    def exists(self, identifier: str, file_type: str) -> bool:
        """True if a file is already stored at `{identifier}.{ext}`."""
        ...

    def url_for(self, af: AudioFile, expires_in: int | None = None) -> str | None:
        """Return a directly-fetchable URL for `af`, or None if the backend
        can't produce one (e.g. local files). Cloud backends return a
        presigned GET URL so the browser can fetch from object storage
        directly, bypassing the FastAPI process."""
        ...


class LocalVaultBackend:
    """Default backend: flat directory under `settings.vault_files_dir`."""

    def path_for(self, identifier: str, file_type: str) -> Path:
        ext = file_type.lstrip(".").lower()
        return settings.vault_files_dir / f"{identifier}.{ext}"

    def resolve(self, af: AudioFile) -> Path:
        if af.identifier and af.file_type:
            vp = self.path_for(af.identifier, af.file_type)
            if vp.exists():
                return vp

        legacy = Path(af.file_path)
        if legacy.is_absolute():
            return legacy
        return settings.music_dir / af.file_path

    def ingest(self, source: Path, identifier: str, file_type: str) -> Path:
        settings.ensure_vault_layout()
        dest = self.path_for(identifier, file_type)
        if not dest.exists():
            shutil.copy2(source, dest)
        return dest

    def exists(self, identifier: str, file_type: str) -> bool:
        return self.path_for(identifier, file_type).exists()

    def url_for(self, af: AudioFile, expires_in: int | None = None) -> str | None:
        """Local files are served by FastAPI itself; no external URL."""
        return None


class CloudVaultBackend:
    """Cloudflare R2 (S3-compatible) hosting.

    boto3 is lazy-imported inside __init__ so the local-only dev path doesn't
    require it at module import time. Objects live at `files/{identifier}.{ext}`
    in the configured bucket — same flat layout as the local vault, just
    remote.

    Media is served to browsers via presigned GET URLs (see `url_for`), which
    the `/api/media/*` router returns as 307 redirects. This bypasses the
    FastAPI process for the actual byte transfer, which is essential when
    every Fly machine has 1 GB of memory and a 33 GB media tree.
    """

    def __init__(self) -> None:
        import boto3  # lazy: keeps the local-dev path boto3-free

        self._s3 = boto3.client(
            "s3",
            endpoint_url=settings.r2_endpoint_url,
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
        )
        self._bucket = settings.r2_bucket

    @staticmethod
    def _key(identifier: str, file_type: str) -> str:
        ext = file_type.lstrip(".").lower()
        return f"files/{identifier}.{ext}"

    def path_for(self, identifier: str, file_type: str) -> Path:
        # PurePosixPath models the "files/foo.m4a" object key. The Protocol
        # advertises Path; PurePosixPath is a sibling of PurePath, so we cast.
        from pathlib import PurePosixPath
        return PurePosixPath(self._key(identifier, file_type))  # type: ignore[return-value]

    def resolve(self, af: AudioFile) -> Path:
        # Callers should prefer `url_for` for cloud storage — this sentinel
        # exists only so the Protocol is satisfied. Local fallthrough paths
        # in the media router check `url_for` first and redirect before
        # ever reaching resolve.
        return self.path_for(af.identifier, af.file_type)

    def ingest(self, source: Path, identifier: str, file_type: str) -> Path:
        key = self._key(identifier, file_type)
        self._s3.upload_file(str(source), self._bucket, key)
        return self.path_for(identifier, file_type)

    def exists(self, identifier: str, file_type: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self._s3.head_object(Bucket=self._bucket, Key=self._key(identifier, file_type))
            return True
        except ClientError:
            return False

    def url_for(self, af: AudioFile, expires_in: int | None = None) -> str | None:
        return self._s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self._bucket,
                "Key": self._key(af.identifier, af.file_type),
            },
            ExpiresIn=expires_in or settings.r2_presign_ttl_seconds,
        )


_backend: VaultBackend | None = None


def get_backend() -> VaultBackend:
    """Return the active vault backend, lazily instantiated.

    Reads `settings.media_backend` on first call. Tests that mutate the
    setting should call `reset_backend()` between cases.
    """
    global _backend
    if _backend is None:
        if settings.media_backend == "r2":
            _backend = CloudVaultBackend()
        else:
            _backend = LocalVaultBackend()
    return _backend


def reset_backend() -> None:
    """Drop the cached backend so the next `get_backend()` re-reads settings."""
    global _backend
    _backend = None


def vault_path_for(identifier: str, file_type: str) -> Path:
    """Canonical vault path for a given identifier + extension."""
    return get_backend().path_for(identifier, file_type)


def vault_path_for_audio_file(af: AudioFile) -> Path | None:
    """Vault path for an AudioFile, if it has the required fields."""
    if not af.identifier or not af.file_type:
        return None
    return vault_path_for(af.identifier, af.file_type)


def resolve_audio_path(af: AudioFile) -> Path:
    """Locate an AudioFile on disk.

    Prefers the vault path (new canonical storage). Falls back to the legacy
    file_path field for rows that haven't been migrated yet.
    """
    return get_backend().resolve(af)


def ingest_into_vault(source: Path, identifier: str, file_type: str) -> Path:
    """Copy a source file into the vault as {identifier}.{ext}. Returns the
    vault path. Source file is left in place.

    If the vault already contains a file at the target path, it's kept as-is
    (identifiers are expected to be stable, so repeated ingest of the same
    file is a no-op).
    """
    return get_backend().ingest(source, identifier, file_type)
