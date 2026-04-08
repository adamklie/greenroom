"""Parse REPERTOIRE.md and ROADMAP.md into structured data."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


# --- REPERTOIRE.md parser ---


@dataclass
class ParsedSong:
    title: str
    artist: str | None
    project: str
    is_original: bool
    status: str
    times_practiced: int
    notes: str | None
    location: str | None = None


def _parse_table_rows(lines: list[str]) -> list[dict[str, str]]:
    """Parse a markdown table into a list of dicts keyed by header names."""
    rows = []
    headers: list[str] = []
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not headers:
            headers = [h.lower().strip() for h in cells]
            continue
        # Skip separator row (|---|---|...)
        if all(set(c) <= {"-", ":", " "} for c in cells):
            continue
        row = {}
        for i, h in enumerate(headers):
            row[h] = cells[i] if i < len(cells) else ""
        rows.append(row)
    return rows


# Section name → project key mapping
_SECTION_MAP = {
    "solo covers": "solo",
    "ozone destructors — covers": "ozone_destructors",
    "ozone destructors — originals": "ozone_destructors",
    "sural project (originals with sural)": "sural",
    "joe collaborations (inactive)": "joe",
    "ideas (unfinished)": "ideas",
    "backing tracks available": None,  # skip
}


def parse_repertoire(filepath: Path) -> list[ParsedSong]:
    """Parse REPERTOIRE.md into a list of ParsedSong."""
    text = filepath.read_text()
    songs: list[ParsedSong] = []

    # Split by ## headings
    sections = re.split(r"^## ", text, flags=re.MULTILINE)

    for section in sections[1:]:  # skip preamble
        heading_line = section.split("\n", 1)[0].strip()
        heading_lower = heading_line.lower()

        project = None
        for key, proj in _SECTION_MAP.items():
            if heading_lower.startswith(key):
                project = proj
                break

        if project is None:
            continue

        lines = section.split("\n")
        rows = _parse_table_rows(lines)

        for row in rows:
            title = row.get("song", row.get("song title", "")).strip()
            if not title:
                continue

            artist = row.get("original artist", row.get("artist", "")).strip() or None
            is_original = False
            if artist and artist.startswith("*") and "original" in artist.lower():
                is_original = True
                artist = None
            if project in ("sural", "joe", "ideas"):
                is_original = True
            if "ozone destructors — originals" in heading_lower:
                is_original = True
                artist = None

            status = row.get("status", "idea").strip().lower()
            if status not in ("idea", "rehearsed", "polished", "recorded", "released"):
                status = "idea"

            times_str = row.get("times practiced", row.get("times_practiced", "0")).strip()
            times_practiced = int(times_str) if times_str.isdigit() else 0

            notes = row.get("notes", "").strip() or None
            location = row.get("location", "").strip() or None

            songs.append(ParsedSong(
                title=title,
                artist=artist,
                project=project,
                is_original=is_original,
                status=status,
                times_practiced=times_practiced,
                notes=notes,
                location=location,
            ))

    return songs


# --- ROADMAP.md parser ---


@dataclass
class ParsedRoadmapTask:
    phase: int
    phase_title: str
    category: str
    task_text: str
    completed: bool
    sort_order: int = 0


def parse_roadmap(filepath: Path) -> list[ParsedRoadmapTask]:
    """Parse ROADMAP.md into a list of roadmap tasks."""
    text = filepath.read_text()
    tasks: list[ParsedRoadmapTask] = []

    phase = 0
    phase_title = ""
    category = ""
    sort_order = 0

    for line in text.split("\n"):
        # Match phase headers: ## Phase 1: Foundation (Months 1-2)
        phase_match = re.match(r"^## Phase (\d+):\s*(.+)", line)
        if phase_match:
            phase = int(phase_match.group(1))
            phase_title = phase_match.group(2).strip()
            continue

        # Match category headers: ### Recording & Gear
        cat_match = re.match(r"^### (.+)", line)
        if cat_match and phase > 0:
            category = cat_match.group(1).strip()
            continue

        # Match checkbox items: - [ ] or - [x]
        task_match = re.match(r"^- \[([ xX])\] (.+)", line)
        if task_match and phase > 0:
            completed = task_match.group(1).lower() == "x"
            task_text = task_match.group(2).strip()
            sort_order += 1
            tasks.append(ParsedRoadmapTask(
                phase=phase,
                phase_title=phase_title,
                category=category,
                task_text=task_text,
                completed=completed,
                sort_order=sort_order,
            ))

    return tasks
