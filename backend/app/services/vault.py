"""Vault: canonical flat storage for imported media.

Every AudioFile has a stable identifier (e.g. AF12AB34CD). The vault stores
the file at `vault_dir/files/{identifier}.{ext}`. That's it — no nested
folders, no project-based organization. Human browsability is traded for
a path that's fully derivable from DB metadata, so restoring the DB from a
backup is sufficient to regain access to every file.

Source files on the user's local disk are left alone after import; the
vault copy is the canonical reference.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from app.config import settings
from app.models import AudioFile


def vault_path_for(identifier: str, file_type: str) -> Path:
    """Canonical vault path for a given identifier + extension."""
    ext = file_type.lstrip(".").lower()
    return settings.vault_files_dir / f"{identifier}.{ext}"


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
    vp = vault_path_for_audio_file(af)
    if vp is not None and vp.exists():
        return vp

    legacy = Path(af.file_path)
    if legacy.is_absolute():
        return legacy
    return settings.music_dir / af.file_path


def ingest_into_vault(source: Path, identifier: str, file_type: str) -> Path:
    """Copy a source file into the vault as {identifier}.{ext}. Returns the
    vault path. Source file is left in place.

    If the vault already contains a file at the target path, it's kept as-is
    (identifiers are expected to be stable, so repeated ingest of the same
    file is a no-op).
    """
    settings.ensure_vault_layout()
    dest = vault_path_for(identifier, file_type)
    if not dest.exists():
        shutil.copy2(source, dest)
    return dest
