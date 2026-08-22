"""WAV / FLAC export using soundfile (no external dependencies)."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


def export_wav(samples: np.ndarray, sample_rate: int, dest: Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(dest), samples, sample_rate, subtype="PCM_16")
    return dest


def export_flac(samples: np.ndarray, sample_rate: int, dest: Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(dest), samples, sample_rate, format="FLAC")
    return dest
