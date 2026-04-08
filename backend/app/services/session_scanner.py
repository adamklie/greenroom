"""Scan Ozone Destructors practice sessions and parse cuts.txt files."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass
class ParsedTake:
    clip_name: str
    source_video: str | None
    start_time: str
    end_time: str
    video_path: str | None  # relative to music_dir
    audio_path: str | None  # relative to music_dir


@dataclass
class ParsedSession:
    session_date: date
    project: str
    folder_path: str  # relative to music_dir
    takes: list[ParsedTake]


def _parse_session_date(folder_name: str) -> date | None:
    """Parse date from folder name like '2026-3-1' or '2025-12-14'."""
    parts = folder_name.split("-")
    if len(parts) != 3:
        return None
    try:
        return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except (ValueError, IndexError):
        return None


def _parse_cuts_txt(cuts_path: Path) -> list[tuple[str | None, str, str, str]]:
    """Parse a cuts.txt file.

    Returns list of (source_video, start_time, end_time, clip_name).
    """
    results = []
    current_video = None

    for line in cuts_path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue

        # Comment line like "# GX010031.MP4 cuts"
        if line.startswith("#"):
            video_match = re.search(r"(GX\d+\.MP4)", line, re.IGNORECASE)
            if video_match:
                current_video = video_match.group(1)
            continue

        # Data line: "00:06:30 00:11:00 your_touch"
        parts = line.split()
        if len(parts) >= 3 and ":" in parts[0] and ":" in parts[1]:
            start = parts[0]
            end = parts[1]
            clip_name = parts[2]
            results.append((current_video, start, end, clip_name))

    return results


def scan_sessions(music_dir: Path) -> list[ParsedSession]:
    """Scan all practice session folders and return structured data."""
    sessions_dir = music_dir / "Ozone Destructors" / "Practice Sessions"
    if not sessions_dir.exists():
        return []

    sessions = []
    audio_exports_dir = music_dir / "_audio_exports" / "Ozone Destructors"

    for folder in sorted(sessions_dir.iterdir()):
        if not folder.is_dir():
            continue

        session_date = _parse_session_date(folder.name)
        if session_date is None:
            continue

        folder_rel = str(folder.relative_to(music_dir))

        # Parse cuts.txt if it exists
        cuts_file = folder / "cuts.txt"
        takes = []

        if cuts_file.exists():
            parsed = _parse_cuts_txt(cuts_file)
            for source_video, start, end, clip_name in parsed:
                # Look for video clip
                video_clip = folder / "cuts" / f"{clip_name}.mp4"
                video_path = None
                if video_clip.exists():
                    video_path = str(video_clip.relative_to(music_dir))

                # Look for audio export (date-prefixed)
                audio_path = None
                audio_dir = audio_exports_dir / folder.name
                if audio_dir.exists():
                    # Try date-prefixed format: 2026-3-1_your_touch.m4a
                    prefixed = audio_dir / f"{folder.name}_{clip_name}.m4a"
                    unprefixed = audio_dir / f"{clip_name}.m4a"
                    if prefixed.exists():
                        audio_path = str(prefixed.relative_to(music_dir))
                    elif unprefixed.exists():
                        audio_path = str(unprefixed.relative_to(music_dir))

                takes.append(ParsedTake(
                    clip_name=clip_name,
                    source_video=source_video,
                    start_time=start,
                    end_time=end,
                    video_path=video_path,
                    audio_path=audio_path,
                ))

        sessions.append(ParsedSession(
            session_date=session_date,
            project="ozone_destructors",
            folder_path=folder_rel,
            takes=takes,
        ))

    return sessions
