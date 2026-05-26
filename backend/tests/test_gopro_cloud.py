"""Cloud-mode tests for the GoPro processing flow.

These tests pin down two contracts:

1. `POST /api/gopro/upload-raw` streams an UploadFile into R2 at
   `raw/{timestamp}_{filename}` and returns the resulting key + a
   presigned playback URL. boto3 is mocked so no real R2 credentials are
   needed.

2. `POST /api/gopro/process` in cloud mode resolves `source_path` as an R2
   object key, downloads it to /tmp, slices with ffmpeg, uploads each cut
   to R2 at `files/{identifier}.mp4`, and inserts AudioFile rows pointing
   at the vault filename. The subprocess call is mocked — we only verify
   the I/O calls are made in the right order.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.config import settings
from app.models import AudioFile, PracticeSession


# --- /api/gopro/upload-raw ---


def test_upload_raw_returns_r2_key(client, monkeypatch):
    """POST /api/gopro/upload-raw in cloud mode streams the file into R2 at
    raw/<timestamp>_<safe-filename> and returns the key + a presigned URL.

    boto3 is stubbed via the fake backend so the test doesn't need real
    credentials."""
    monkeypatch.setattr(settings, "media_backend", "r2")

    fake_s3 = MagicMock()
    fake_s3.generate_presigned_url.return_value = "https://example.r2.dev/raw/x.mp4?sig=x"
    fake_backend = MagicMock()
    fake_backend._s3 = fake_s3
    fake_backend._bucket = "greenroom-1-media"
    monkeypatch.setattr("app.routers.gopro.get_backend", lambda: fake_backend)

    fake_video_bytes = b"\x00" * 1024  # 1 KB fake video payload
    response = client.post(
        "/api/gopro/upload-raw",
        files={"file": ("My Practice Video.mp4", fake_video_bytes, "video/mp4")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["size_bytes"] == 1024

    # R2 key matches expected pattern: raw/YYYYMMDDTHHMMSS_<sanitized>
    assert body["r2_key"].startswith("raw/")
    assert re.match(r"^raw/\d{8}T\d{6}_My_Practice_Video\.mp4$", body["r2_key"]), body["r2_key"]
    # source_path mirrors r2_key in cloud mode (frontend submits source_path).
    assert body["source_path"] == body["r2_key"]

    # boto3 upload_file was called against the right bucket + key.
    fake_s3.upload_file.assert_called_once()
    args, _ = fake_s3.upload_file.call_args
    _, bucket, key = args
    assert bucket == "greenroom-1-media"
    assert key == body["r2_key"]

    # Presigned URL was generated.
    fake_s3.generate_presigned_url.assert_called_once()
    assert body["playback_url"] == "https://example.r2.dev/raw/x.mp4?sig=x"


def test_upload_raw_local_mode_writes_to_vault_raw(client, tmp_path, monkeypatch):
    """In local mode, upload-raw writes to vault_dir/raw/ and returns the
    absolute filesystem path (no R2 involvement)."""
    monkeypatch.setattr(settings, "media_backend", "local")

    response = client.post(
        "/api/gopro/upload-raw",
        files={"file": ("clip.mp4", b"\x00" * 512, "video/mp4")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["ok"] is True
    assert body["r2_key"] is None
    assert body["size_bytes"] == 512

    # The file landed under vault_dir/raw/.
    raw_dir = settings.vault_dir / "raw"
    assert raw_dir.exists()
    assert (raw_dir / "clip.mp4").exists()
    assert body["source_path"] == str(raw_dir / "clip.mp4")


def test_upload_raw_sanitizes_filename(client, monkeypatch):
    """Whitespace and risky characters are stripped from the leaf name in
    the R2 key — no path traversal, no spaces."""
    monkeypatch.setattr(settings, "media_backend", "r2")

    fake_s3 = MagicMock()
    fake_s3.generate_presigned_url.return_value = "https://example/url"
    fake_backend = MagicMock()
    fake_backend._s3 = fake_s3
    fake_backend._bucket = "bucket"
    monkeypatch.setattr("app.routers.gopro.get_backend", lambda: fake_backend)

    response = client.post(
        "/api/gopro/upload-raw",
        files={"file": ("../../../etc/Weird Name!@#.mp4", b"x", "video/mp4")},
    )
    assert response.status_code == 200
    body = response.json()
    # Path components stripped, special chars dropped, spaces -> underscores.
    assert "/etc/" not in body["r2_key"]
    assert ".." not in body["r2_key"]
    assert body["r2_key"].endswith("Weird_Name.mp4")


# --- /api/gopro/process in cloud mode ---


def test_process_session_cloud_downloads_and_uploads(client, db, monkeypatch):
    """End-to-end cloud branch: download from R2, ffmpeg, upload cuts,
    insert AudioFile rows. Subprocess is mocked so we don't need real
    ffmpeg in CI."""
    monkeypatch.setattr(settings, "media_backend", "r2")

    fake_s3 = MagicMock()
    # download_file writes a sentinel byte so subsequent ffmpeg (mocked
    # below) sees an "input" file — but we don't actually need the real
    # download to do anything, just track the call.
    fake_backend = MagicMock()
    fake_backend._s3 = fake_s3
    fake_backend._bucket = "greenroom-1-media"
    monkeypatch.setattr(
        "app.services.gopro_processor.get_backend", lambda: fake_backend
    )

    # Mock ffmpeg via subprocess.run — pretend it succeeded and produced
    # the expected cut file. We need to actually create the file because
    # boto3 upload_file reads from it (mocked, so it doesn't actually read,
    # but the code path passes str(path) to upload_file regardless).
    def fake_run(cmd, **kwargs):
        # The last argument is the output path. Touch it so the (mocked)
        # upload_file call has a real string path to receive.
        out_path = Path(cmd[-1])
        out_path.write_bytes(b"fake-cut")
        rc = MagicMock()
        rc.returncode = 0
        rc.stderr = b""
        rc.stdout = b""
        return rc

    with patch("app.services.gopro_processor.subprocess.run", side_effect=fake_run):
        response = client.post(
            "/api/gopro/process",
            json={
                "source_path": "raw/20260525T220000_practice.mp4",
                "session_date": "2026-01-01",
                "project": "ozone_destructors",
                "clips": [
                    {
                        "start_seconds": 0,
                        "end_seconds": 30,
                        "clip_name": "song one",
                        "song_id": None,
                    },
                    {
                        "start_seconds": 30,
                        "end_seconds": 60,
                        "clip_name": "song two",
                        "song_id": None,
                    },
                ],
            },
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["clips_processed"] == 2
    assert body["errors"] == []
    assert body["cuts_txt_path"] == ""  # no cuts.txt in cloud mode

    # boto3 download_file was called once for the raw video.
    fake_s3.download_file.assert_called_once()
    dl_args, _ = fake_s3.download_file.call_args
    assert dl_args[0] == "greenroom-1-media"
    assert dl_args[1] == "raw/20260525T220000_practice.mp4"

    # Two cuts uploaded to files/{identifier}.mp4.
    assert fake_s3.upload_file.call_count == 2
    upload_keys = [call.args[2] for call in fake_s3.upload_file.call_args_list]
    for key in upload_keys:
        assert key.startswith("files/")
        assert key.endswith(".mp4")

    # DB rows inserted: 2 AudioFiles + 1 PracticeSession.
    afs = db.query(AudioFile).all()
    assert len(afs) == 2
    for af in afs:
        assert af.role == "practice_clip"
        assert af.file_type == "mp4"
        assert af.identifier and af.identifier.startswith("AF")
        # file_path is just the vault filename (matches upload.py convention)
        assert af.file_path == f"{af.identifier}.mp4"

    sessions = db.query(PracticeSession).all()
    assert len(sessions) == 1
    assert sessions[0].date == date(2026, 1, 1)
    # Folder path is the logical layout, no actual fs directory created.
    assert sessions[0].folder_path == "Ozone Destructors/Practice Sessions/2026-1-1"


def test_process_session_cloud_skips_zero_duration_clips(client, db, monkeypatch):
    """Cloud-mode processor reports invalid (zero/negative duration) clips
    in `errors` and doesn't attempt to upload them."""
    monkeypatch.setattr(settings, "media_backend", "r2")

    fake_s3 = MagicMock()
    fake_backend = MagicMock()
    fake_backend._s3 = fake_s3
    fake_backend._bucket = "bucket"
    monkeypatch.setattr(
        "app.services.gopro_processor.get_backend", lambda: fake_backend
    )

    with patch("app.services.gopro_processor.subprocess.run") as mock_run:
        response = client.post(
            "/api/gopro/process",
            json={
                "source_path": "raw/test.mp4",
                "session_date": "2026-01-01",
                "clips": [
                    {"start_seconds": 10, "end_seconds": 10, "clip_name": "bad", "song_id": None},
                ],
            },
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["clips_processed"] == 0
    assert any("Invalid duration" in e for e in body["errors"])
    # ffmpeg should never have been called for the bad clip.
    mock_run.assert_not_called()
    # No cuts uploaded.
    fake_s3.upload_file.assert_not_called()
