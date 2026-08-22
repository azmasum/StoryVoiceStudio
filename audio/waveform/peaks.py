"""Waveform peak extraction for UI previews (cached to disk)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import soundfile as sf

from app.config.paths import analysis_cache_dir


def _cache_key(path: str, blocks: int) -> str:
    stat = Path(path).stat()
    raw = f"{path}|{stat.st_size}|{stat.st_mtime_ns}|{blocks}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def extract_peaks(audio_path: str | Path, blocks: int = 2000,
                  use_cache: bool = True) -> list[float]:
    """Return min/max-normalized absolute peaks per block for fast drawing."""
    audio_path = str(audio_path)
    key = _cache_key(audio_path, blocks)
    cache_file = analysis_cache_dir() / f"peaks_{key}.json"
    if use_cache and cache_file.exists():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if len(data) == blocks:
                return data
        except Exception:  # noqa: BLE001
            pass

    with sf.SoundFile(audio_path) as handle:
        frames = len(handle)
        block_len = max(1, frames // blocks)
        peaks: list[float] = []
        for start in range(0, frames, max(1, frames // blocks)):
            handle.seek(start)
            segment = handle.read(block_len, dtype="float32", always_2d=True)
            if not len(segment):
                break
            peaks.append(float(np.max(np.abs(segment))))
    top = max(peaks, default=1.0) or 1.0
    normalized = [round(p / top, 4) for p in peaks]

    if use_cache:
        try:
            cache_file.write_text(json.dumps(normalized), encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    return normalized
