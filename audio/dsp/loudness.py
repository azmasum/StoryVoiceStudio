"""Loudness measurement and normalization (ITU-R BS.1770 via pyloudnorm)."""
from __future__ import annotations

import numpy as np
import pyloudnorm as pyln


def integrated_lufs(samples: np.ndarray, sample_rate: int) -> float:
    """Integrated loudness in LUFS."""
    if len(samples) < sample_rate // 5:  # too short to measure reliably
        return -70.0
    meter = pyln.Meter(sample_rate)
    audio = samples if samples.ndim == 1 else np.mean(samples, axis=1)
    try:
        return float(meter.integrated_loudness(audio.astype(np.float64)))
    except ValueError:
        return -70.0


def short_term_lufs(samples: np.ndarray, sample_rate: int,
                    window_seconds: float = 3.0) -> np.ndarray:
    """Short-term loudness curve (one value per 100 ms)."""
    meter = pyln.Meter(sample_rate)
    block = int(sample_rate * 0.1)
    window = int(sample_rate * window_seconds)
    values = []
    for start in range(0, max(1, len(samples) - window + 1), block):
        segment = samples[start:start + window]
        if len(segment) < window // 2:
            break
        try:
            values.append(float(meter.integrated_loudness(segment)))
        except ValueError:
            values.append(-70.0)
    return np.array(values)


def peak_dbfs(samples: np.ndarray) -> float:
    peak = float(np.max(np.abs(samples))) if len(samples) else 0.0
    return float(20 * np.log10(max(peak, 1e-9)))


def true_peak_dbfs(samples: np.ndarray, sample_rate: int,
                   oversample: int = 4) -> float:
    """Approximate true peak by 4x oversampling (polyphase interpolation)."""
    if len(samples) == 0:
        return -70.0
    from scipy.signal import resample_poly

    upsampled = resample_poly(samples, oversample, 1)
    peak = float(np.max(np.abs(upsampled)))
    _ = sample_rate
    return float(20 * np.log10(max(peak, 1e-9)))


def normalize_to_lufs(samples: np.ndarray, sample_rate: int, target_lufs: float,
                      ceiling_dbtp: float = -1.5) -> tuple[np.ndarray, dict]:
    """Normalize to *target_lufs*, shaving true peaks via a limiter.

    A naive uniform scale-down sacrifices loudness whenever a single peak
    exceeds the ceiling; a transparent limiter keeps narration at the
    requested integrated level instead.
    """
    from audio.dsp.dynamics import limiter as _limiter

    audio = samples.astype(np.float32)
    before = integrated_lufs(audio, sample_rate)
    if before > -69.0:
        gain_db = target_lufs - before
        audio = audio * float(10 ** (gain_db / 20.0))

    tp = true_peak_dbfs(audio, sample_rate)
    peak_limited = False
    if tp > ceiling_dbtp:
        # Shave peaks transparently, then reclaim any leftover loudness.
        audio = _limiter(audio, sample_rate, ceiling_db=ceiling_dbtp - 0.2)
        peak_limited = True
        after_limit = integrated_lufs(audio, sample_rate)
        shortfall = target_lufs - after_limit
        headroom = ceiling_dbtp - true_peak_dbfs(audio, sample_rate)
        recover_db = min(shortfall, headroom)
        if recover_db > 0.05:
            audio = audio * float(10 ** (recover_db / 20.0))

    stats = {
        "lufs_before": round(before, 2),
        "lufs_after": round(integrated_lufs(audio, sample_rate), 2),
        "true_peak_after": round(true_peak_dbfs(audio, sample_rate), 2),
        "peak_limited": peak_limited,
    }
    return audio.astype(np.float32), stats
