"""Scan the music directory for standalone audio/video files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".aac", ".flac"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".MP4"}

# Directories to skip during scanning
SKIP_DIRS = {"greenroom", ".claude", "_audio_exports", "Ozone Destructors"}


@dataclass
class ParsedAudioFile:
    file_path: str  # relative to music_dir
    file_type: str  # extension without dot
    source: str  # 'solo', 'sural', 'joe', 'ideas', 'backing_track', etc.
    song_title_hint: str  # best guess at song title from filename
    version: str | None  # 'v1', 'v3', etc.


def _extract_version(filename: str) -> str | None:
    """Extract version string like 'v6' from a filename."""
    match = re.search(r"\b(v\d+)\b", filename, re.IGNORECASE)
    return match.group(1).lower() if match else None


def _guess_title(filename: str, source: str) -> str:
    """Best-effort extraction of song title from filename."""
    name = Path(filename).stem

    # Strip date prefix like "2025_01_25_" or "2025-09-11_"
    name = re.sub(r"^\d{4}[-_]\d{1,2}[-_]\d{1,2}[-_]?", "", name)

    # Strip version suffixes
    name = re.sub(r"\s*v\d+\b.*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*(copy|FINAL|master|remaster\w*)\b.*", "", name, flags=re.IGNORECASE)

    # Strip "adam " prefix from ideas
    name = re.sub(r"^adam\s+\d+\s*", "", name, flags=re.IGNORECASE)

    # Replace underscores with spaces
    name = name.replace("_", " ").strip()

    return name if name else Path(filename).stem


def _scan_directory(
    dir_path: Path, source: str, music_dir: Path
) -> list[ParsedAudioFile]:
    """Recursively scan a directory for audio files."""
    results = []
    if not dir_path.exists():
        return results

    for f in sorted(dir_path.rglob("*")):
        if not f.is_file():
            continue
        if f.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        # Skip files inside .band GarageBand bundles
        if ".band" in str(f):
            continue

        rel_path = str(f.relative_to(music_dir))
        results.append(ParsedAudioFile(
            file_path=rel_path,
            file_type=f.suffix.lstrip(".").lower(),
            source=source,
            song_title_hint=_guess_title(f.name, source),
            version=_extract_version(f.name),
        ))

    return results


def scan_media(music_dir: Path) -> list[ParsedAudioFile]:
    """Scan all music directories for standalone audio files."""
    files: list[ParsedAudioFile] = []

    # Solo recordings (top-level audio only, skip subdirs with raw WAVs)
    solo_dir = music_dir / "Solo"
    if solo_dir.exists():
        for f in sorted(solo_dir.iterdir()):
            if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS:
                files.append(ParsedAudioFile(
                    file_path=str(f.relative_to(music_dir)),
                    file_type=f.suffix.lstrip(".").lower(),
                    source="solo",
                    song_title_hint=_guess_title(f.name, "solo"),
                    version=None,
                ))

    # Sural project
    files.extend(_scan_directory(music_dir / "Sural", "sural", music_dir))

    # Joe collaborations
    files.extend(_scan_directory(music_dir / "Joe", "joe", music_dir))

    # Ideas
    files.extend(_scan_directory(music_dir / "Ideas", "ideas", music_dir))

    # Backing tracks
    files.extend(_scan_directory(music_dir / "Backing Tracks", "backing_track", music_dir))

    # Ozone Destructors finished recordings (not practice sessions)
    od_runaway = music_dir / "Ozone Destructors" / "Runaway Train"
    files.extend(_scan_directory(od_runaway, "ozone_destructors", music_dir))

    return files
