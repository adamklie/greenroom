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
import tempfile
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from sqlalchemy.orm import Session as DBSession

from app.config import settings
from app.models import AudioFile, PracticeSession
from app.models.audio_file import generate_identifier
from app.services.vault import get_backend, is_cloud_backend

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
    existing_session_id: int | None = None,
) -> ProcessResult:
    """Process clips: cut videos, extract audio, create DB records.

    If existing_session_id is given, clips are added to that session and
    written into its folder (cuts.txt is appended, not overwritten).

    In cloud mode (`media_backend='r2'`), `source_directory` is interpreted
    as an R2 object key (e.g. `raw/20260525T2200_practice.mp4`). The raw
    video is downloaded to a tempdir, sliced with ffmpeg, and each cut is
    uploaded to R2 at `files/{identifier}.{ext}`. The cuts.txt file is
    skipped (no shared filesystem to write it to).
    """
    if is_cloud_backend():
        return _process_session_cloud(
            db=db,
            source_key=source_directory,
            session_date=session_date,
            clips=clips,
            project=project,
            existing_session_id=existing_session_id,
        )
    return _process_session_local(
        db=db,
        source_directory=source_directory,
        session_date=session_date,
        clips=clips,
        project=project,
        existing_session_id=existing_session_id,
    )


def _process_session_local(
    db: DBSession,
    source_directory: str,
    session_date: date,
    clips: list[ClipMarker],
    project: str,
    existing_session_id: int | None,
) -> ProcessResult:
    """Original local-filesystem processing path. Writes cuts into the
    music_dir layout and inserts DB rows pointing at the relative paths."""
    errors: list[str] = []
    source_dir = Path(source_directory)

    # Resolve target session + folder
    session: PracticeSession | None = None
    if existing_session_id is not None:
        session = db.query(PracticeSession).get(existing_session_id)
        if not session:
            raise ValueError(f"Session {existing_session_id} not found")
        session_folder = settings.music_dir / session.folder_path
        date_str = f"{session.date.year}-{session.date.month}-{session.date.day}"
    else:
        date_str = f"{session_date.year}-{session_date.month}-{session_date.day}"
        session_folder = settings.music_dir / "Ozone Destructors" / "Practice Sessions" / date_str

    cuts_folder = session_folder / "cuts"
    cuts_folder.mkdir(parents=True, exist_ok=True)

    audio_folder = settings.music_dir / "_audio_exports" / "Ozone Destructors" / date_str
    audio_folder.mkdir(parents=True, exist_ok=True)

    # Write cuts.txt (append if adding to existing session)
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
    new_cuts_text = "\n".join(cuts_lines) + "\n"
    if existing_session_id is not None and cuts_txt_path.exists():
        prior = cuts_txt_path.read_text()
        if not prior.endswith("\n"):
            prior += "\n"
        cuts_txt_path.write_text(prior + new_cuts_text)
    else:
        cuts_txt_path.write_text(new_cuts_text)

    # Create DB session if not provided
    folder_rel = str(session_folder.relative_to(settings.music_dir))
    if session is None:
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

        # Audio extraction happens on demand via the "Extract audio" button
        # in the Library view. Processing only produces the video clip.
        video_rel = str(video_out.relative_to(settings.music_dir))
        recorded_at_dt = datetime.combine(session.date, datetime.min.time())
        start_tc = _seconds_to_timecode(clip.start_seconds)
        end_tc = _seconds_to_timecode(clip.end_seconds)

        for path_rel, ftype in [(video_rel, "mp4")]:
            if db.query(AudioFile).filter_by(file_path=path_rel).first():
                continue
            db.add(AudioFile(
                song_id=clip.song_id,
                file_path=path_rel,
                file_type=ftype,
                identifier=generate_identifier(Path(path_rel).name, recorded_at_dt.isoformat()),
                source=project,
                role="practice_clip",
                is_stem=False,
                session_id=session.id,
                clip_name=safe_name,
                source_file=clip.source_video,
                start_time=start_tc,
                end_time=end_tc,
                video_path=video_rel,
                recorded_at=recorded_at_dt,
            ))

    db.commit()
    return ProcessResult(
        session_id=session.id, session_date=date_str,
        clips_processed=clips_processed, audio_extracted=audio_extracted,
        errors=errors, cuts_txt_path=str(cuts_txt_path.relative_to(settings.music_dir)),
    )


def _process_session_cloud(
    db: DBSession,
    source_key: str,
    session_date: date,
    clips: list[ClipMarker],
    project: str,
    existing_session_id: int | None,
) -> ProcessResult:
    """Cloud-mode processing path.

    `source_key` is an R2 object key (e.g. `raw/20260525T2200_practice.mp4`).
    The raw video is downloaded to a tempdir, ffmpeg `-c copy` slices each
    clip locally, then each cut is uploaded to R2 at `files/{identifier}.mp4`.

    There is no shared filesystem to write cuts.txt to, so it's skipped. DB
    rows are inserted with `file_path={identifier}.mp4` (same convention as
    `routers/upload.py` uses for cloud uploads — the vault filename only,
    `files/` prefix is implied by the backend).

    The raw R2 object is intentionally left in place after processing; a
    future cleanup script can sweep `raw/` separately.
    """
    errors: list[str] = []
    backend = get_backend()
    # CloudVaultBackend specifics — _s3 and _bucket. We don't go through the
    # Protocol here because we need download + raw-key uploads, neither of
    # which are part of the VaultBackend Protocol.
    s3 = backend._s3  # type: ignore[attr-defined]
    bucket = backend._bucket  # type: ignore[attr-defined]

    # Resolve target session
    session: PracticeSession | None = None
    if existing_session_id is not None:
        session = db.query(PracticeSession).get(existing_session_id)
        if not session:
            raise ValueError(f"Session {existing_session_id} not found")
        date_str = f"{session.date.year}-{session.date.month}-{session.date.day}"
        folder_rel = session.folder_path
    else:
        date_str = f"{session_date.year}-{session_date.month}-{session_date.day}"
        # Logical folder path used only as a DB pointer in cloud mode (no
        # actual directory is created). Mirrors the local layout so the
        # session row looks identical across modes.
        folder_rel = f"Ozone Destructors/Practice Sessions/{date_str}"

    if session is None:
        existing_session = db.query(PracticeSession).filter_by(folder_path=folder_rel).first()
        if existing_session:
            session = existing_session
        else:
            session = PracticeSession(date=session_date, project=project, folder_path=folder_rel)
            db.add(session)
            db.flush()

    clips_processed = 0
    audio_extracted = 0

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        local_video = tmpdir_path / "input.mp4"

        # Download raw video from R2 once; reuse for all clips.
        try:
            s3.download_file(bucket, source_key, str(local_video))
        except Exception as e:
            raise RuntimeError(f"Failed to download raw video from R2 ({source_key}): {e}")

        for clip in clips:
            safe_name = _sanitize_name(clip.clip_name)
            duration = clip.end_seconds - clip.start_seconds
            if duration <= 0:
                errors.append(f"Invalid duration for {clip.clip_name}")
                continue

            cut_out = tmpdir_path / f"{safe_name}.mp4"
            try:
                subprocess.run([
                    FFMPEG, "-ss", str(clip.start_seconds), "-i", str(local_video),
                    "-t", str(duration), "-c", "copy", "-y", str(cut_out),
                ], capture_output=True, timeout=120, check=True)
                clips_processed += 1
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                errors.append(f"Failed to cut {clip.clip_name}: {e}")
                continue

            recorded_at_dt = datetime.combine(session.date, datetime.min.time())
            identifier = generate_identifier(f"{safe_name}.mp4", recorded_at_dt.isoformat())
            ftype = "mp4"

            # Upload to R2 at files/{identifier}.{ext}.
            try:
                s3.upload_file(str(cut_out), bucket, f"files/{identifier}.{ftype}")
            except Exception as e:
                errors.append(f"Failed to upload cut {clip.clip_name} to R2: {e}")
                continue

            # DB row: file_path is just the vault filename (matches the
            # convention upload.py uses for cloud-vault rows).
            vault_name = f"{identifier}.{ftype}"
            if db.query(AudioFile).filter_by(file_path=vault_name).first():
                continue

            start_tc = _seconds_to_timecode(clip.start_seconds)
            end_tc = _seconds_to_timecode(clip.end_seconds)
            db.add(AudioFile(
                song_id=clip.song_id,
                file_path=vault_name,
                file_type=ftype,
                identifier=identifier,
                source=project,
                role="practice_clip",
                is_stem=False,
                session_id=session.id,
                clip_name=safe_name,
                source_file=Path(source_key).name,
                start_time=start_tc,
                end_time=end_tc,
                video_path=vault_name,
                recorded_at=recorded_at_dt,
            ))

    db.commit()
    return ProcessResult(
        session_id=session.id, session_date=date_str,
        clips_processed=clips_processed, audio_extracted=audio_extracted,
        errors=errors, cuts_txt_path="",  # no cuts.txt in cloud mode
    )
