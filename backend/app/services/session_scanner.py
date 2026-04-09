"""Scan Ozone Destructors practice sessions and parse cuts.txt files.

Handles three folder structures:
1. Early (clipped/): 2025-06-22 through 2025-11-23 — clips in clipped/, no cuts.txt
2. Middle (cuts/ or clipped/, per-video cuts files): some have GX*_cuts.txt
3. Modern (cuts.txt + cuts/): 2026-1-10 onward — full pipeline
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

VIDEO_EXTS = {".mp4", ".mov", ".MP4"}


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


def _parse_cuts_file(cuts_path: Path) -> list[tuple[str | None, str, str, str]]:
    """Parse a cuts.txt or GX*_cuts.txt file.

    Returns list of (source_video, start_time, end_time, clip_name).
    """
    results = []
    current_video = None

    # If filename is like GX010012_cuts.txt, extract the video name
    fname = cuts_path.stem
    if fname.startswith("GX") and fname.endswith("_cuts"):
        current_video = fname.replace("_cuts", "") + ".MP4"

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

        # Data line: "00:06:30 00:11:00 your_touch" or "00:00:00 00:02:00 losing_cells.mov"
        parts = line.split()
        if len(parts) >= 3 and ":" in parts[0] and ":" in parts[1]:
            start = parts[0]
            end = parts[1]
            clip_name = parts[2]
            # Strip file extension from clip name if present
            clip_name = re.sub(r"\.\w{2,4}$", "", clip_name)
            results.append((current_video, start, end, clip_name))

    return results


def _find_audio_export(
    clip_name: str, folder_name: str, audio_exports_dir: Path, music_dir: Path
) -> str | None:
    """Search for an audio export matching a clip name."""
    audio_dir = audio_exports_dir / folder_name
    if not audio_dir.exists():
        return None

    # Normalize clip name (strip extensions, lowercase for matching)
    clean = re.sub(r"\.\w{2,4}$", "", clip_name)

    # Try exact patterns
    candidates = [
        audio_dir / f"{folder_name}_{clean}.m4a",          # date-prefixed
        audio_dir / f"{clean}.m4a",                         # unprefixed
        audio_dir / f"{folder_name}_{clip_name}.m4a",       # with original name
    ]
    for c in candidates:
        if c.exists():
            return str(c.relative_to(music_dir))

    # Fuzzy: search for any file containing the clip name
    clean_lower = clean.lower().replace("_", " ")
    for f in audio_dir.iterdir():
        if f.suffix.lower() != ".m4a":
            continue
        fname_lower = f.stem.lower().replace("_", " ")
        # Strip date prefix for comparison
        fname_no_date = re.sub(r"^\d{4}-\d{1,2}-\d{1,2}[_ ]?", "", fname_lower)
        if clean_lower == fname_no_date or clean_lower in fname_no_date:
            return str(f.relative_to(music_dir))

    return None


def _find_video_clip(
    clip_name: str, folder: Path, music_dir: Path
) -> str | None:
    """Search for a video clip in cuts/ or clipped/ directories."""
    clean = re.sub(r"\.\w{2,4}$", "", clip_name)

    for subdir_name in ["cuts", "clipped"]:
        subdir = folder / subdir_name
        if not subdir.exists():
            continue
        for ext in [".mp4", ".mov", ".MP4"]:
            candidate = subdir / f"{clean}{ext}"
            if candidate.exists():
                return str(candidate.relative_to(music_dir))
        # Also try with original clip_name (might include extension)
        for f in subdir.iterdir():
            if f.stem == clean and f.suffix.lower() in {".mp4", ".mov"}:
                return str(f.relative_to(music_dir))

    return None


def _scan_clips_directory(
    folder: Path, subdir_name: str, folder_name: str,
    audio_exports_dir: Path, music_dir: Path
) -> list[ParsedTake]:
    """Scan a clipped/ or cuts/ directory directly (no cuts.txt)."""
    subdir = folder / subdir_name
    if not subdir.exists():
        return []

    takes = []
    for f in sorted(subdir.iterdir()):
        if not f.is_file() or f.suffix.lower() not in {".mp4", ".mov"}:
            continue

        clip_name = f.stem  # e.g., "your_touch" or "Feel Good Inc"
        video_path = str(f.relative_to(music_dir))
        audio_path = _find_audio_export(clip_name, folder_name, audio_exports_dir, music_dir)

        takes.append(ParsedTake(
            clip_name=clip_name,
            source_video=None,
            start_time="",
            end_time="",
            video_path=video_path,
            audio_path=audio_path,
        ))

    return takes


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
        takes: list[ParsedTake] = []

        # Strategy 1: Modern cuts.txt (single file with all timestamps)
        cuts_file = folder / "cuts.txt"
        if cuts_file.exists():
            parsed = _parse_cuts_file(cuts_file)
            for source_video, start, end, clip_name in parsed:
                video_path = _find_video_clip(clip_name, folder, music_dir)
                audio_path = _find_audio_export(
                    clip_name, folder.name, audio_exports_dir, music_dir
                )
                takes.append(ParsedTake(
                    clip_name=clip_name,
                    source_video=source_video,
                    start_time=start,
                    end_time=end,
                    video_path=video_path,
                    audio_path=audio_path,
                ))

        # Strategy 2: Per-video cuts files (GX010012_cuts.txt)
        if not takes:
            per_video_cuts = sorted(folder.glob("GX*_cuts.txt"))
            for pv_file in per_video_cuts:
                parsed = _parse_cuts_file(pv_file)
                for source_video, start, end, clip_name in parsed:
                    video_path = _find_video_clip(clip_name, folder, music_dir)
                    audio_path = _find_audio_export(
                        clip_name, folder.name, audio_exports_dir, music_dir
                    )
                    takes.append(ParsedTake(
                        clip_name=clip_name,
                        source_video=source_video,
                        start_time=start,
                        end_time=end,
                        video_path=video_path,
                        audio_path=audio_path,
                    ))

        # Strategy 3: Fallback — scan clipped/ or cuts/ directory directly
        if not takes:
            for subdir_name in ["clipped", "cuts"]:
                takes = _scan_clips_directory(
                    folder, subdir_name, folder.name, audio_exports_dir, music_dir
                )
                if takes:
                    break

        sessions.append(ParsedSession(
            session_date=session_date,
            project="ozone_destructors",
            folder_path=folder_rel,
            takes=takes,
        ))

    return sessions
