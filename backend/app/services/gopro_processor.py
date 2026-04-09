"""GoPro session processor — cut videos and extract audio.

Uses energy-based analysis (not silence detection) to find gaps between
songs in band practice recordings. Calibrated against real Ozone Destructors
sessions where typical song levels are -14 to -18 dB and gaps are -22 to -30 dB.
"""

from __future__ import annotations

import math
import re
import struct
import subprocess
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.models import PracticeSession, Take

FFMPEG = "/Users/adamklie/opt/ffmpeg"
if not Path(FFMPEG).exists():
    FFMPEG = "ffmpeg"

VIDEO_EXTS = {".mp4", ".MP4", ".mov", ".MOV"}


@dataclass
class ProposedClip:
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    suggested_name: str


@dataclass
class EnergyPoint:
    time: float
    db: float


@dataclass
class AnalysisResult:
    video_path: str
    duration_seconds: float
    proposed_clips: list[ProposedClip]
    energy_profile: list[EnergyPoint]  # for visualization
    median_db: float
    threshold_db: float


@dataclass
class ClipMarker:
    source_video: str
    start_seconds: float
    end_seconds: float
    clip_name: str
    song_id: int | None = None


@dataclass
class ProcessResult:
    session_id: int
    session_date: str
    clips_processed: int
    audio_extracted: int
    errors: list[str]
    cuts_txt_path: str


def _seconds_to_timecode(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _sanitize_name(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9_\- ]", "", name)
    name = name.replace(" ", "_")
    return name or "unnamed"


def _get_duration(video_path: str) -> float:
    """Get video duration using ffmpeg."""
    result = subprocess.run(
        [FFMPEG, "-i", video_path], capture_output=True, text=True, timeout=10,
    )
    for line in result.stderr.split("\n"):
        if "Duration:" in line:
            match = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", line)
            if match:
                h, m, s, ms = match.groups()
                return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 100
    return 0


def _compute_energy_profile(video_path: str, window_seconds: float = 3.0) -> list[EnergyPoint]:
    """Compute RMS energy in dB over time using raw audio extraction.

    This is MUCH better than silencedetect for band practice rooms because
    it measures relative energy changes, not absolute silence.
    """
    sample_rate = 8000
    window_samples = int(sample_rate * window_seconds)

    result = subprocess.run(
        [
            FFMPEG, "-i", video_path,
            "-af", f"aresample={sample_rate},aformat=sample_fmts=s16",
            "-ac", "1",
            "-f", "s16le", "-",
        ],
        capture_output=True, timeout=600,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Audio extraction failed: {result.stderr[:200]}")

    data = result.stdout
    samples = struct.unpack(f"{len(data) // 2}h", data)

    profile = []
    for i in range(0, len(samples), window_samples):
        chunk = samples[i:i + window_samples]
        if len(chunk) < window_samples // 2:
            break
        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk))
        db = 20 * math.log10(max(rms, 1) / 32768)
        t = i / sample_rate
        profile.append(EnergyPoint(time=t, db=round(db, 1)))

    return profile


def analyze_video(
    video_path: str,
    drop_db: float = 6.0,
    min_gap_duration: float = 2.0,
    min_clip_duration: float = 30.0,
    window_seconds: float = 3.0,
) -> AnalysisResult:
    """Analyze a video using energy-based gap detection.

    Instead of looking for absolute silence, this finds regions where
    the energy drops significantly below the median — which is how
    "between songs" actually sounds in a live practice room.

    Args:
        video_path: Path to the video file
        drop_db: How many dB below median counts as a "gap" (default 6)
        min_gap_duration: Minimum gap duration in seconds (default 2)
        min_clip_duration: Minimum clip duration in seconds (default 30)
        window_seconds: Energy analysis window size (default 3)
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    duration = _get_duration(video_path)
    if duration == 0:
        raise ValueError(f"Could not determine duration of {video_path}")

    # Compute energy profile
    profile = _compute_energy_profile(video_path, window_seconds)
    if not profile:
        raise ValueError("No audio data extracted")

    # Calculate median energy (typical "playing" level)
    db_values = sorted(p.db for p in profile)
    median_db = db_values[len(db_values) // 2]
    threshold_db = median_db - drop_db

    # Find "gap" regions where energy drops below threshold
    gaps: list[tuple[float, float]] = []
    gap_start = None

    for p in profile:
        if p.db < threshold_db:
            if gap_start is None:
                gap_start = p.time
        else:
            if gap_start is not None:
                gap_end = p.time
                if gap_end - gap_start >= min_gap_duration:
                    gaps.append((gap_start, gap_end))
                gap_start = None

    # Handle gap at the end
    if gap_start is not None and profile[-1].time - gap_start >= min_gap_duration:
        gaps.append((gap_start, profile[-1].time))

    # Derive clips from gaps
    proposed_clips: list[ProposedClip] = []
    clip_num = 1

    if not gaps:
        proposed_clips.append(ProposedClip(
            start_seconds=0, end_seconds=duration,
            duration_seconds=duration, suggested_name=f"clip_{clip_num}",
        ))
    else:
        # Before first gap
        if gaps[0][0] > min_clip_duration:
            proposed_clips.append(ProposedClip(
                start_seconds=0,
                end_seconds=round(gaps[0][0], 1),
                duration_seconds=round(gaps[0][0], 1),
                suggested_name=f"clip_{clip_num}",
            ))
            clip_num += 1

        # Between gaps
        for i in range(len(gaps) - 1):
            clip_start = round(gaps[i][1], 1)
            clip_end = round(gaps[i + 1][0], 1)
            clip_duration = clip_end - clip_start
            if clip_duration >= min_clip_duration:
                proposed_clips.append(ProposedClip(
                    start_seconds=clip_start,
                    end_seconds=clip_end,
                    duration_seconds=round(clip_duration, 1),
                    suggested_name=f"clip_{clip_num}",
                ))
                clip_num += 1

        # After last gap
        last_gap_end = round(gaps[-1][1], 1)
        remaining = duration - last_gap_end
        if remaining > min_clip_duration:
            proposed_clips.append(ProposedClip(
                start_seconds=last_gap_end,
                end_seconds=round(duration, 1),
                duration_seconds=round(remaining, 1),
                suggested_name=f"clip_{clip_num}",
            ))

    return AnalysisResult(
        video_path=video_path,
        duration_seconds=round(duration, 1),
        proposed_clips=proposed_clips,
        energy_profile=profile,
        median_db=round(median_db, 1),
        threshold_db=round(threshold_db, 1),
    )


def list_video_files(directory: str) -> list[dict]:
    dir_path = Path(directory)
    if not dir_path.exists():
        return []
    files = []
    for f in sorted(dir_path.iterdir()):
        if f.is_file() and f.suffix in VIDEO_EXTS:
            size_mb = f.stat().st_size / (1024 * 1024)
            files.append({
                "filename": f.name,
                "path": str(f),
                "size_mb": round(size_mb, 1),
                "extension": f.suffix,
            })
    return files


def process_session(
    db: DBSession,
    source_directory: str,
    session_date: date,
    clips: list[ClipMarker],
    project: str = "ozone_destructors",
) -> ProcessResult:
    """Process clips: cut videos, extract audio, create DB records."""
    errors: list[str] = []
    source_dir = Path(source_directory)

    date_str = f"{session_date.year}-{session_date.month}-{session_date.day}"

    session_folder = settings.music_dir / "Ozone Destructors" / "Practice Sessions" / date_str
    cuts_folder = session_folder / "cuts"
    cuts_folder.mkdir(parents=True, exist_ok=True)

    audio_folder = settings.music_dir / "_audio_exports" / "Ozone Destructors" / date_str
    audio_folder.mkdir(parents=True, exist_ok=True)

    # Write cuts.txt
    cuts_txt_path = session_folder / "cuts.txt"
    current_video = None
    cuts_lines = []
    for clip in clips:
        if clip.source_video != current_video:
            current_video = clip.source_video
            cuts_lines.append(f"# {current_video} cuts")
        start_tc = _seconds_to_timecode(clip.start_seconds)
        end_tc = _seconds_to_timecode(clip.end_seconds)
        cuts_lines.append(f"{start_tc} {end_tc} {_sanitize_name(clip.clip_name)}")
    cuts_txt_path.write_text("\n".join(cuts_lines) + "\n")

    # Create DB session
    folder_rel = str(session_folder.relative_to(settings.music_dir))
    existing_session = db.query(PracticeSession).filter_by(folder_path=folder_rel).first()
    if existing_session:
        session = existing_session
    else:
        session = PracticeSession(date=session_date, project=project, folder_path=folder_rel)
        db.add(session)
        db.flush()

    clips_processed = 0
    audio_extracted = 0

    for clip in clips:
        safe_name = _sanitize_name(clip.clip_name)
        source_file = source_dir / clip.source_video
        if not source_file.exists():
            errors.append(f"Source video not found: {clip.source_video}")
            continue

        duration = clip.end_seconds - clip.start_seconds
        if duration <= 0:
            errors.append(f"Invalid duration for {clip.clip_name}")
            continue

        # Cut video
        video_out = cuts_folder / f"{safe_name}.mp4"
        try:
            subprocess.run([
                FFMPEG, "-ss", str(clip.start_seconds), "-i", str(source_file),
                "-t", str(duration), "-c", "copy", "-y", str(video_out),
            ], capture_output=True, timeout=120, check=True)
            clips_processed += 1
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            errors.append(f"Failed to cut {clip.clip_name}: {e}")
            continue

        # Extract audio
        audio_out = audio_folder / f"{date_str}_{safe_name}.m4a"
        try:
            subprocess.run([
                FFMPEG, "-i", str(video_out), "-vn", "-acodec", "aac",
                "-b:a", "192k", "-y", str(audio_out),
            ], capture_output=True, timeout=60, check=True)
            audio_extracted += 1
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            errors.append(f"Failed to extract audio for {clip.clip_name}: {e}")

        # Create Take
        video_rel = str(video_out.relative_to(settings.music_dir))
        audio_rel = str(audio_out.relative_to(settings.music_dir)) if audio_out.exists() else None

        existing_take = db.query(Take).filter_by(
            session_id=session.id, clip_name=safe_name
        ).first()
        if not existing_take:
            db.add(Take(
                session_id=session.id, song_id=clip.song_id,
                clip_name=safe_name, source_video=clip.source_video,
                start_time=_seconds_to_timecode(clip.start_seconds),
                end_time=_seconds_to_timecode(clip.end_seconds),
                video_path=video_rel, audio_path=audio_rel,
            ))

    db.commit()
    return ProcessResult(
        session_id=session.id, session_date=date_str,
        clips_processed=clips_processed, audio_extracted=audio_extracted,
        errors=errors, cuts_txt_path=str(cuts_txt_path.relative_to(settings.music_dir)),
    )
