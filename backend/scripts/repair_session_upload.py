"""One-off repair: backfill missing clips into an existing prod session.

A folder import to prod left only some of the files in the session (the rest
failed mid-upload). This re-uploads ONLY the files that are missing from the
session — it diffs the local directory against what the session already
contains (by submitted filename), so it's idempotent: safe to re-run.

Auth: the API gates on the browser session cookie + active project. Grab both
from your logged-in browser (DevTools > Application > Cookies on
greenroom-1.fly.dev):
    GR_COOKIE   -> value of the `greenroom_session` cookie
    GR_PROJECT  -> value of the `greenroom_project` cookie (the active project id)

Usage:
    GR_COOKIE=... GR_PROJECT=... \
      python backend/scripts/repair_session_upload.py \
        --dir ~/Desktop/music/2026_06_14 --date 2026-06-14 [--apply]

Without --apply it's a dry run: it prints what it WOULD upload and uploads
nothing.
"""

import argparse
import os
import sys
from pathlib import Path

import requests

BASE = os.environ.get("GR_BASE", "https://greenroom-1.fly.dev")
MEDIA_EXTS = {".m4a", ".mp3", ".wav", ".aac", ".flac", ".ogg", ".aiff", ".aif",
              ".mp4", ".mov", ".avi", ".mkv", ".m4v"}


def session_headers():
    cookie = os.environ.get("GR_COOKIE")
    project = os.environ.get("GR_PROJECT")
    if not cookie:
        sys.exit("GR_COOKIE is required (greenroom_session cookie value)")
    if not project:
        sys.exit("GR_PROJECT is required (greenroom_project cookie value / active project id)")
    return (
        {"Cookie": f"greenroom_session={cookie}", "X-Greenroom-Project": project},
        project,
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="Local directory of clips")
    ap.add_argument("--date", required=True, help="Session date YYYY-MM-DD (to find the session)")
    ap.add_argument("--session-id", type=int, help="Skip the date lookup; target this session id")
    ap.add_argument("--apply", action="store_true", help="Actually upload (default: dry run)")
    args = ap.parse_args()

    headers, project = session_headers()
    src = Path(os.path.expanduser(args.dir))
    if not src.is_dir():
        sys.exit(f"Not a directory: {src}")

    local = sorted(
        p for p in src.iterdir()
        if p.is_file() and p.suffix.lower() in MEDIA_EXTS and not p.name.startswith(".")
    )
    print(f"Local: {len(local)} media files in {src}")

    # Resolve the target session.
    if args.session_id:
        session_id = args.session_id
    else:
        r = requests.get(f"{BASE}/api/sessions", headers=headers, timeout=30)
        r.raise_for_status()
        matches = [s for s in r.json() if str(s.get("date")) == args.date]
        if not matches:
            sys.exit(f"No session found for date {args.date}. Sessions: "
                     + ", ".join(f"{s['id']}:{s.get('name')}({s.get('date')})" for s in r.json()))
        if len(matches) > 1:
            print("Multiple sessions on that date — pass --session-id to disambiguate:")
            for s in matches:
                print(f"  id={s['id']} name={s.get('name')!r} tracks={s.get('track_count')}")
            sys.exit(1)
        session_id = matches[0]["id"]
        print(f"Session: id={session_id} name={matches[0].get('name')!r} "
              f"date={matches[0].get('date')} existing_tracks={matches[0].get('track_count')}")

    # What's already in the session?
    r = requests.get(f"{BASE}/api/sessions/{session_id}", headers=headers, timeout=30)
    r.raise_for_status()
    existing = r.json().get("audio_files", [])
    # Older rows stored submitted_file_name WITH a folder prefix
    # (e.g. "2026_06_14/go.mp4") before the strip-prefix fix. Match on the
    # basename so those still count as present.
    have = {Path(af["submitted_file_name"]).name
            for af in existing if af.get("submitted_file_name")}
    print(f"Session already has {len(existing)} files.")

    missing = [p for p in local if p.name not in have]
    print(f"\nMissing from session: {len(missing)}")
    for p in missing:
        print(f"  + {p.name}  ({p.stat().st_size / 1e6:.1f} MB)")

    if not missing:
        print("\nNothing to do — session already contains every local file.")
        return
    if not args.apply:
        print("\nDRY RUN — re-run with --apply to upload these.")
        return

    print("\nUploading...")
    ok, fail = 0, 0
    for p in missing:
        with open(p, "rb") as fh:
            data = {
                "source": "unknown",
                "role": "practice_clip",
                "project": project,
                "session_id": str(session_id),
            }
            files = {"file": (p.name, fh, "video/mp4")}
            try:
                resp = requests.post(f"{BASE}/api/upload", headers=headers,
                                     data=data, files=files, timeout=600)
                if resp.ok:
                    ok += 1
                    print(f"  ok  {p.name} -> af#{resp.json().get('audio_file_id')}")
                else:
                    fail += 1
                    print(f"  ERR {p.name}: {resp.status_code} {resp.text[:200]}")
            except Exception as e:  # noqa: BLE001
                fail += 1
                print(f"  ERR {p.name}: {e}")

    print(f"\nDone: {ok} uploaded, {fail} failed. Session now has "
          f"{len(existing) + ok} files (target {len(local)}).")


if __name__ == "__main__":
    main()
