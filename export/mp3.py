"""MP3 export through FFmpeg."""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from app.utils.errors import UserFacingError
from export.ffmpeg import ffmpeg_available, wav_to_mp3
from export.wav import export_wav

log = logging.getLogger("render")


def export_mp3(samples: np.ndarray, sample_rate: int, dest: Path,
               bitrate: str = "192k") -> Path:
    """Render a temp WAV then transcode with FFmpeg."""
    if not ffmpeg_available():
        raise UserFacingError(
            what="MP3 export requires FFmpeg.",
            why="MP3 encoding is provided by the external FFmpeg tool, which "
                "is not installed on this computer.",
            actions=[
                "Install FFmpeg and add it to PATH.",
                "Or set the STORYVOICE_FFMPEG environment variable to "
                "ffmpeg.exe.",
                "WAV export works without FFmpeg - use it instead.",
            ],
        )
    dest = Path(dest).with_suffix(".mp3")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_wav = dest.with_suffix(".tmp.wav")
    export_wav(samples, sample_rate, tmp_wav)
    try:
        wav_to_mp3(tmp_wav, dest, bitrate=bitrate)
    finally:
        tmp_wav.unlink(missing_ok=True)
    log.info("Exported MP3: %s", dest)
    return dest


__all__ = ["export_mp3"]
