"""GoPro session processor — cut videos and extract audio.

Takes a list of marked clip regions, runs ffmpeg to extract video clips
and audio, organizes into practice session folders, and creates DB records.
"""

from __future__ import annotations

import subprocess
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.models import PracticeSession, Song, Take

FFMPEG = "/Users/adamklie/opt/ffmpeg"
# Fall back to system ffmpeg if custom path doesn't exist
if not Path(FFMPEG).exists():
    FFMPEG = "ffmpeg"

VIDEO_EXTS = {".mp4", ".MP4", ".mov", ".MOV"}


@dataclass
class ProposedClip:
    """An auto-detected clip region from silence analysis."""
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    suggested_name: str  # "clip_1", "clip_2", etc.


@dataclass
class AnalysisResult:
    """Result of analyzing a video file for clip boundaries."""
    video_path: str
    duration_seconds: float
    proposed_clips: list[ProposedClip]
    silence_gaps: list[tuple[float, float]]  # (start, end) of each silence


def analyze_video(
    video_path: str,
    silence_threshold_db: int = -30,
    min_silence_duration: float = 3.0,
    min_clip_duration: float = 30.0,
) -> AnalysisResult:
    """Analyze a video file to detect silence gaps and propose clip boundaries.

    Uses ffmpeg silencedetect filter to find gaps between songs.
    """
    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    # Get duration from ffmpeg
    duration_result = subprocess.run(
        [FFMPEG, "-i", str(path)],
        capture_output=True, text=True, timeout=10,
    )
    duration_seconds = 0.0
    for line in duration_result.stderr.split("\n"):
        if "Duration:" in line:
            match = re.search(r"Duration: (\d+):(\d+):(\d+)\.(\d+)", line)
            if match:
                h, m, s, ms = match.groups()
                duration_seconds = int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 100

    if duration_seconds == 0:
        raise ValueError(f"Could not determine duration of {video_path}")

    # Run silence detection
    result = subprocess.run(
        [
            FFMPEG, "-i", str(path),
            "-af", f"silencedetect=noise={silence_threshold_db}dB:d={min_silence_duration}",
            "-f", "null", "-",
        ],
        capture_output=True, text=True, timeout=int(duration_seconds * 0.1) + 60,
    )

    # Parse silence events from stderr
    silence_gaps: list[tuple[float, float]] = []
    silence_start = None

    for line in result.stderr.split("\n"):
        start_match = re.search(r"silence_start: ([\d.]+)", line)
        end_match = re.search(r"silence_end: ([\d.]+)", line)

        if start_match:
            silence_start = float(start_match.group(1))
        if end_match and silence_start is not None:
            silence_end = float(end_match.group(1))
            silence_gaps.append((silence_start, silence_end))
            silence_start = None

    # Derive clip boundaries from silence gaps
    # Each clip is the region BETWEEN two silence gaps
    proposed_clips: list[ProposedClip] = []
    clip_num = 1

    if not silence_gaps:
        # No silence detected — the whole video is one clip
        proposed_clips.append(ProposedClip(
            start_seconds=0,
            end_seconds=duration_seconds,
            duration_seconds=duration_seconds,
            suggested_name=f"clip_{clip_num}",
        ))
    else:
        # First clip: from start to first silence
        if silence_gaps[0][0] > min_clip_duration:
            proposed_clips.append(ProposedClip(
                start_seconds=0,
                end_seconds=silence_gaps[0][0],
                duration_seconds=silence_gaps[0][0],
                suggested_name=f"clip_{clip_num}",
            ))
            clip_num += 1

        # Middle clips: between consecutive silences
        for i in range(len(silence_gaps) - 1):
            clip_start = silence_gaps[i][1]  # end of this silence
            clip_end = silence_gaps[i + 1][0]  # start of next silence
            clip_duration = clip_end - clip_start

            if clip_duration >= min_clip_duration:
                proposed_clips.append(ProposedClip(
                    start_seconds=round(clip_start, 1),
                    end_seconds=round(clip_end, 1),
                    duration_seconds=round(clip_duration, 1),
                    suggested_name=f"clip_{clip_num}",
                ))
                clip_num += 1

        # Last clip: from last silence to end
        last_silence_end = silence_gaps[-1][1]
        remaining = duration_seconds - last_silence_end
        if remaining > min_clip_duration:
            proposed_clips.append(ProposedClip(
                start_seconds=round(last_silence_end, 1),
                end_seconds=round(duration_seconds, 1),
                duration_seconds=round(remaining, 1),
                suggested_name=f"clip_{clip_num}",
            ))

    return AnalysisResult(
        video_path=video_path,
        duration_seconds=round(duration_seconds, 1),
        proposed_clips=proposed_clips,
        silence_gaps=[(round(s, 1), round(e, 1)) for s, e in silence_gaps],
    )


@dataclass
class ClipMarker:
    """A marked region in a video file."""
    source_video: str  # filename (e.g., "GX010033.MP4")
    start_seconds: float
    end_seconds: float
    clip_name: str  # user-provided name (e.g., "your_touch")
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
    """Convert seconds to HH:MM:SS format."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _sanitize_name(name: str) -> str:
    """Sanitize a clip name for filesystem use."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9_\- ]", "", name)
    name = name.replace(" ", "_")
    return name or "unnamed"


def list_video_files(directory: str) -> list[dict]:
    """List video files in a directory."""
    dir_path = Path(directory)
    if not dir_path.exists():
        return []

    files = []
    for f in sorted(dir_path.iterdir()):
        if f.is_file() and f.suffix in VIDEO_EXTS:
            # Get file size and duration estimate
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
    """Process a GoPro session: cut videos, extract audio, create DB records.

    1. Creates session folder in Practice Sessions/
    2. Writes cuts.txt for archival compatibility
    3. Runs ffmpeg to cut each clip from source video
    4. Extracts audio from each clip
    5. Creates PracticeSession + Take records in DB
    """
    errors: list[str] = []
    source_dir = Path(source_directory)

    # Format date for folder name (matching existing convention: YYYY-M-D)
    date_str = f"{session_date.year}-{session_date.month}-{session_date.day}"

    # Create session folder
    session_folder = settings.music_dir / "Ozone Destructors" / "Practice Sessions" / date_str
    cuts_folder = session_folder / "cuts"
    cuts_folder.mkdir(parents=True, exist_ok=True)

    # Create audio export folder
    audio_folder = settings.music_dir / "_audio_exports" / "Ozone Destructors" / date_str
    audio_folder.mkdir(parents=True, exist_ok=True)

    # Write cuts.txt (archival compatibility)
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

    # Create DB session record
    folder_rel = str(session_folder.relative_to(settings.music_dir))
    existing_session = db.query(PracticeSession).filter_by(folder_path=folder_rel).first()
    if existing_session:
        session = existing_session
    else:
        session = PracticeSession(
            date=session_date,
            project=project,
            folder_path=folder_rel,
        )
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

        # Calculate duration
        duration = clip.end_seconds - clip.start_seconds
        if duration <= 0:
            errors.append(f"Invalid duration for {clip.clip_name}: {duration}s")
            continue

        # Cut video clip
        video_out = cuts_folder / f"{safe_name}.mp4"
        try:
            subprocess.run([
                FFMPEG,
                "-ss", str(clip.start_seconds),
                "-i", str(source_file),
                "-t", str(duration),
                "-c", "copy",
                "-y",
                str(video_out),
            ], capture_output=True, timeout=120, check=True)
            clips_processed += 1
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            errors.append(f"Failed to cut {clip.clip_name}: {e}")
            continue

        # Extract audio
        audio_out = audio_folder / f"{date_str}_{safe_name}.m4a"
        try:
            subprocess.run([
                FFMPEG,
                "-i", str(video_out),
                "-vn", "-acodec", "aac", "-b:a", "192k",
                "-y",
                str(audio_out),
            ], capture_output=True, timeout=60, check=True)
            audio_extracted += 1
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            errors.append(f"Failed to extract audio for {clip.clip_name}: {e}")

        # Create Take record
        video_rel = str(video_out.relative_to(settings.music_dir))
        audio_rel = str(audio_out.relative_to(settings.music_dir)) if audio_out.exists() else None

        existing_take = db.query(Take).filter_by(
            session_id=session.id, clip_name=safe_name
        ).first()

        if not existing_take:
            take = Take(
                session_id=session.id,
                song_id=clip.song_id,
                clip_name=safe_name,
                source_video=clip.source_video,
                start_time=_seconds_to_timecode(clip.start_seconds),
                end_time=_seconds_to_timecode(clip.end_seconds),
                video_path=video_rel,
                audio_path=audio_rel,
            )
            db.add(take)

    db.commit()

    return ProcessResult(
        session_id=session.id,
        session_date=date_str,
        clips_processed=clips_processed,
        audio_extracted=audio_extracted,
        errors=errors,
        cuts_txt_path=str(cuts_txt_path.relative_to(settings.music_dir)),
    )
