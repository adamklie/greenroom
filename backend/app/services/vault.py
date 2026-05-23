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


class CloudVaultBackend:
    """Stub for Cloudflare R2 (S3-compatible) hosting.

    Not wired yet — `MEDIA_BACKEND=r2` will instantiate this class but every
    operation raises. Phase 3 of the deployment work adds boto3 + credentials
    + actual upload/download.
    """

    _ERR = (
        "R2 backend not yet wired — set R2_* env vars and ensure boto3 is "
        "installed when MEDIA_BACKEND=r2"
    )

    def path_for(self, identifier: str, file_type: str) -> Path:
        raise NotImplementedError(self._ERR)

    def resolve(self, af: AudioFile) -> Path:
        raise NotImplementedError(self._ERR)

    def ingest(self, source: Path, identifier: str, file_type: str) -> Path:
        raise NotImplementedError(self._ERR)

    def exists(self, identifier: str, file_type: str) -> bool:
        raise NotImplementedError(self._ERR)


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
