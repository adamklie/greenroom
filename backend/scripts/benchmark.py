"""Benchmark Greenroom API endpoints.

Hits each endpoint N times (first call = cold, rest = warm) and prints a
summary with cold/p50/p95 timings. Appends one JSON line per run to
benchmarks.jsonl so trends are trivial to diff.

Usage:
    python -m scripts.benchmark                # defaults, 8 warm + 1 cold per endpoint
    python -m scripts.benchmark --host http://localhost:8000 --warm 20
    python -m scripts.benchmark --only songs,dashboard
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
import urllib.request
from datetime import datetime
from pathlib import Path


DEFAULT_ENDPOINTS: list[tuple[str, str]] = [
    ("dashboard",          "/api/dashboard"),
    ("songs",              "/api/songs"),
    ("audio_files",        "/api/audio-files"),
    ("audio_files_song",   "/api/audio-files?has_song=true"),
    ("sessions",           "/api/sessions"),
    ("recommendations",    "/api/recommendations"),
    ("apple_stats",        "/api/apple-music/stats"),
    ("apple_suggestions",  "/api/apple-music/suggestions?limit=50"),
    ("triage",             "/api/triage"),
    ("tags",               "/api/tags"),
    ("options",            "/api/options"),
    ("setlists",           "/api/setlists"),
    ("activity",           "/api/dashboard"),  # placeholder; swap as needed
]

# Timings are in seconds; flag anything above this as slow.
WARN_SECONDS = 0.5


def _hit(url: str, timeout: float = 30.0) -> tuple[int, float]:
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            r.read()
            return r.status, time.perf_counter() - start
    except Exception:
        return 0, time.perf_counter() - start


def run(host: str, warm: int, only: set[str] | None) -> dict:
    endpoints = [(n, p) for n, p in DEFAULT_ENDPOINTS if not only or n in only]
    rows: list[dict] = []

    for name, path in endpoints:
        url = host.rstrip("/") + path
        _status, cold = _hit(url)
        warms = [_hit(url)[1] for _ in range(warm)]
        warms_sorted = sorted(warms)
        p50 = statistics.median(warms) if warms else 0.0
        p95 = warms_sorted[int(0.95 * (len(warms) - 1))] if warms else 0.0
        max_w = max(warms) if warms else 0.0
        rows.append({
            "name": name, "path": path, "status": _status,
            "cold_s": round(cold, 4),
            "warm_p50_s": round(p50, 4),
            "warm_p95_s": round(p95, 4),
            "warm_max_s": round(max_w, 4),
            "warm_samples": len(warms),
        })

    return {"ts": datetime.now().isoformat(timespec="seconds"), "host": host, "warm_n": warm, "results": rows}


def print_table(report: dict) -> None:
    rows = report["results"]
    hdr = f"{'endpoint':<22}{'cold':>8}{'p50':>8}{'p95':>8}{'max':>8}  status"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        flag = "!" if r["warm_p95_s"] > WARN_SECONDS else " "
        print(f"{r['name']:<22}{r['cold_s']:>8.3f}{r['warm_p50_s']:>8.3f}{r['warm_p95_s']:>8.3f}{r['warm_max_s']:>8.3f}  {r['status']} {flag}")


def append_log(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(report) + "\n")


def _load_last_n(path: Path, n: int) -> list[dict]:
    if not path.exists():
        return []
    lines = path.read_text().strip().splitlines()
    return [json.loads(l) for l in lines[-n:] if l.strip()]


def compare(path: Path) -> None:
    runs = _load_last_n(path, 2)
    if len(runs) < 2:
        print(f"Need at least 2 runs in {path}; found {len(runs)}.")
        return
    before, after = runs
    before_by = {r["name"]: r for r in before["results"]}
    after_by = {r["name"]: r for r in after["results"]}
    print(f"BEFORE: {before['ts']}")
    print(f"AFTER : {after['ts']}")
    print()
    print(f"{'endpoint':<22}{'p50 before':>12}{'p50 after':>12}{'Δ%':>8}  {'p95 before':>12}{'p95 after':>12}{'Δ%':>8}")
    print("-" * 88)
    for name in sorted(set(before_by) | set(after_by)):
        b, a = before_by.get(name), after_by.get(name)
        if not (b and a):
            continue
        def pct(x, y):
            return (y - x) / x * 100 if x else 0.0
        p50_d = pct(b["warm_p50_s"], a["warm_p50_s"])
        p95_d = pct(b["warm_p95_s"], a["warm_p95_s"])
        flag = "  " if abs(p95_d) < 20 else ("↑ " if p95_d > 0 else "↓ ")
        print(f"{name:<22}{b['warm_p50_s']:>12.4f}{a['warm_p50_s']:>12.4f}{p50_d:>7.1f}%  "
              f"{b['warm_p95_s']:>12.4f}{a['warm_p95_s']:>12.4f}{p95_d:>7.1f}% {flag}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://localhost:8000")
    ap.add_argument("--warm", type=int, default=8)
    ap.add_argument("--only", default="", help="comma-separated endpoint names")
    ap.add_argument("--log", default="benchmarks.jsonl")
    ap.add_argument("--compare", action="store_true", help="show diff of last two runs and exit")
    args = ap.parse_args()

    log_path = Path(args.log)
    if args.compare:
        compare(log_path)
        return

    only = {s.strip() for s in args.only.split(",") if s.strip()} or None
    report = run(args.host, args.warm, only)
    print_table(report)
    append_log(report, log_path)
    print(f"\nAppended to {args.log} (use --compare to diff vs previous run)")


if __name__ == "__main__":
    main()
