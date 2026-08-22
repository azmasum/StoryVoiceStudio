"""Music track management: import, validation, mood tagging."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from audio.analysis.resample import resample_to

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}


@dataclass
class MusicTrack:
    path: str
    category: str = "Cinematic"
    gain_db: float = -18.0
    fade_in_seconds: float = 2.0
    fade_out_seconds: float = 4.0


def is_supported_audio(path: str | Path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def load_music(path: str | Path, target_rate: int) -> tuple[np.ndarray, int]:
    """Load any soundfile-supported audio and resample to *target_rate*."""
    data, rate = sf.read(str(path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if rate != target_rate:
        mono = resample_to(mono, rate, target_rate)
    peak = float(np.max(np.abs(mono))) if len(mono) else 0.0
    if peak > 1.0:
        mono = mono / peak
    return mono.astype(np.float32), target_rate
