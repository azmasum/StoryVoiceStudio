"""Locate and drive FFmpeg for MP3/M4A export.

FFmpeg is not bundled with the repository. We search PATH, common install
locations and an optional ``ffmpeg`` folder next to the executable.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("render")


def find_ffmpeg() -> str | None:
    """Return a usable ffmpeg path, or None when unavailable."""
    override = os.environ.get("STORYVOICE_FFMPEG")
    candidates: list[str] = []
    if override:
        candidates.append(override)
    found = shutil.which("ffmpeg")
    if found:
        return found
    if getattr(sys, "frozen", False):
        local = Path(sys.executable).parent / "ffmpeg" / "ffmpeg.exe"
        candidates.append(str(local))
    for pattern in (
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        str(Path.home() / "ffmpeg" / "bin" / "ffmpeg.exe"),
    ):
        candidates.append(pattern)
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return candidate
    return None


def ffmpeg_available() -> bool:
    return find_ffmpeg() is not None


def run_ffmpeg(args: list[str], timeout_seconds: int = 600) -> None:
    exe = find_ffmpeg()
    if exe is None:
        raise RuntimeError(
            "FFmpeg was not found. Install FFmpeg or set STORYVOICE_FFMPEG "
            "to its full path to enable MP3 export."
        )
    cmd = [exe, "-y", "-hide_banner", "-loglevel", "error", *args]
    log.debug("Running %s", " ".join(cmd))
    result = subprocess.run(cmd, capture_output=True, text=True,
                            timeout=timeout_seconds)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr.strip()[:500]}")


def wav_to_mp3(source_wav: Path, dest_mp3: Path, bitrate: str = "192k") -> None:
    run_ffmpeg([
        "-i", str(source_wav),
        "-codec:a", "libmp3lame",
        "-b:a", bitrate,
        "-ar", "44100",
        str(dest_mp3),
    ])


def wav_to_m4a(source_wav: Path, dest_m4a: Path) -> None:
    run_ffmpeg([
        "-i", str(source_wav),
        "-c:a", "aac",
        "-b:a", "192k",
        str(dest_m4a),
    ])
