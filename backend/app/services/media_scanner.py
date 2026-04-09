"""Scan music directories for standalone audio/video files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

AUDIO_EXTENSIONS = {".m4a", ".mp3", ".wav", ".aac", ".flac"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".MP4"}
ALL_MEDIA_EXTENSIONS = AUDIO_EXTENSIONS | VIDEO_EXTENSIONS

# Directories inside the music dir to skip
SKIP_DIRS = {"greenroom", ".claude", "_audio_exports", "Ozone Destructors"}

# Directories that contain raw stems (not mixed songs)
STEM_DIRS = {"000927_0001", "R1 91!o0001", "QUESTION001", "A01010_0001", "A71010_0001",
             "A71010_0002", "A71010_0003", "A71010_0004"}


@dataclass
class ParsedAudioFile:
    file_path: str  # relative to music_dir or absolute
    file_type: str
    source: str
    song_title_hint: str
    version: str | None
    role: str = "recording"  # recording, reference, backing_track, stem, demo, final_mix
    is_stem: bool = False


def _extract_version(filename: str) -> str | None:
    match = re.search(r"\b(v\d+)\b", filename, re.IGNORECASE)
    return match.group(1).lower() if match else None


def _guess_title(filename: str) -> str:
    name = Path(filename).stem
    # Strip date prefixes
    name = re.sub(r"^\d{4}[-_]\d{1,2}[-_]\d{1,2}[-_]?", "", name)
    # Strip version suffixes
    name = re.sub(r"\s*v\d+\b.*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*(copy|FINAL|master|remaster\w*)\b.*", "", name, flags=re.IGNORECASE)
    # Strip "adam " or date prefix patterns from ~/Music files
    name = re.sub(r"^adam\s+\d+\s*", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*-\s*\d{1,2}[/_]\d{1,2}[/_]\d{2,4},?\s*\d{1,2}\.\d{2}\s*(AM|PM)?\.?$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s*--\s*Adam.*$", "", name, flags=re.IGNORECASE)
    name = name.replace("_", " ").strip()
    return name if name else Path(filename).stem


def _scan_directory(
    dir_path: Path, source: str, base_dir: Path, recursive: bool = True
) -> list[ParsedAudioFile]:
    results = []
    if not dir_path.exists():
        return results

    iterator = dir_path.rglob("*") if recursive else dir_path.iterdir()
    for f in sorted(iterator):
        if not f.is_file():
            continue
        if f.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        # Skip GarageBand bundles
        if ".band" in str(f):
            continue
        # Detect stems
        is_stem = f.parent.name in STEM_DIRS and f.suffix.lower() == ".wav"

        rel_path = str(f.relative_to(base_dir)) if str(f).startswith(str(base_dir)) else str(f)
        results.append(ParsedAudioFile(
            file_path=rel_path,
            file_type=f.suffix.lstrip(".").lower(),
            source=source,
            song_title_hint=_guess_title(f.name),
            version=_extract_version(f.name),
            role="stem" if is_stem else "recording",
            is_stem=is_stem,
        ))

    return results


def scan_media(music_dir: Path) -> list[ParsedAudioFile]:
    """Scan all known music directories for audio files."""
    files: list[ParsedAudioFile] = []

    # Solo recordings (recursive now — catches grad_housing etc.)
    files.extend(_scan_directory(music_dir / "Solo", "solo", music_dir, recursive=True))

    # Sural project
    files.extend(_scan_directory(music_dir / "Sural", "collaborator", music_dir))

    # Joe collaborations
    files.extend(_scan_directory(music_dir / "Joe", "collaborator", music_dir))

    # Ideas
    files.extend(_scan_directory(music_dir / "Ideas", "phone", music_dir))

    # Backing tracks
    for f in _scan_directory(music_dir / "Backing Tracks", "download", music_dir):
        f.role = "backing_track"
        files.append(f)

    # Ozone Destructors finished recordings
    files.extend(_scan_directory(
        music_dir / "Ozone Destructors" / "Runaway Train", "ozone_destructors", music_dir
    ))

    # ~/Music/ top-level files (NEW)
    home_music = Path.home() / "Music"
    if home_music.exists():
        for f in sorted(home_music.iterdir()):
            if not f.is_file() or f.suffix.lower() not in ALL_MEDIA_EXTENSIONS:
                continue
            files.append(ParsedAudioFile(
                file_path=str(f),
                file_type=f.suffix.lstrip(".").lower(),
                source="unknown",
                song_title_hint=_guess_title(f.name),
                version=_extract_version(f.name),
            ))

    # ~/Desktop/ loose music files (NEW)
    desktop = Path.home() / "Desktop"
    if desktop.exists():
        for f in sorted(desktop.iterdir()):
            if not f.is_file():
                continue
            if f.suffix.lower() not in ALL_MEDIA_EXTENSIONS:
                continue
            # Skip GoPro raw files (those go through session scanner)
            if f.name.startswith("GX") and f.suffix.upper() == ".MP4":
                continue
            files.append(ParsedAudioFile(
                file_path=str(f),
                file_type=f.suffix.lstrip(".").lower(),
                source="unknown",
                song_title_hint=_guess_title(f.name),
                version=_extract_version(f.name),
            ))

    return files
