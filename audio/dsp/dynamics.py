"""Dynamic range processing: compressor and brickwall limiter."""
from __future__ import annotations

import numpy as np

from audio.dsp.filters import envelope_follow


def _db_to_linear(db: float) -> float:
    return float(10 ** (db / 20.0))


def _linear_to_db(value: float) -> float:
    return float(20 * np.log10(max(value, 1e-10)))


def compressor(samples: np.ndarray, sample_rate: int,
               threshold_db: float = -24.0, ratio: float = 3.0,
               attack_ms: float = 15.0, release_ms: float = 120.0,
               makeup: bool = False) -> np.ndarray:
    """Feed-forward downward compressor with smoothed gain computer."""
    if len(samples) == 0:
        return samples.astype(np.float32)
    env = envelope_follow(samples, sample_rate, attack_ms, release_ms)
    env_db = 20.0 * np.log10(np.maximum(env, 1e-8))
    over = np.maximum(env_db - threshold_db, 0.0)
    gain_reduction_db = over * (1.0 / ratio - 1.0)   # <= 0
    gain = (10 ** (gain_reduction_db / 20.0)).astype(np.float32)
    out = samples * gain
    if makeup:
        reduction_avg = float(np.mean(gain_reduction_db))
        compensation = _db_to_linear(-reduction_avg * 0.7)
        out = out * compensation
    return np.clip(out, -1.0, 1.0).astype(np.float32)


def limiter(samples: np.ndarray, sample_rate: int,
            ceiling_db: float = -1.5, lookahead_ms: float = 5.0,
            release_ms: float = 60.0) -> np.ndarray:
    """Lookahead brickwall limiter that keeps true peaks under *ceiling_db*."""
    if len(samples) == 0:
        return samples.astype(np.float32)
    ceiling = _db_to_linear(ceiling_db)
    look = max(1, int(sample_rate * lookahead_ms / 1000.0))
    padded = np.abs(np.pad(samples.astype(np.float64), (look, 0),
                           mode="edge"))
    # Sliding max over the lookahead window without materialising one
    # full-length copy per lookahead sample (O(N) time and memory).
    from scipy.ndimage import maximum_filter1d

    future_peak = maximum_filter1d(
        padded, size=look, origin=-(look // 2), mode="nearest"
    )[: len(samples)]
    needed_gain = np.minimum(
        ceiling / np.maximum(future_peak, 1e-9), 1.0
    ).astype(np.float64)

    # Smooth gain trajectory so limiting stays transparent.
    block = max(1, sample_rate // 200)
    n_blocks = len(needed_gain) // block + (len(needed_gain) % block != 0)
    coarse_min = np.array([
        needed_gain[i * block:(i + 1) * block].min()
        for i in range(n_blocks)
    ])
    release_coeff = float(np.exp(-block / max(1e-6, sample_rate * release_ms / 1000.0)))
    smooth = np.zeros_like(coarse_min)
    level = 1.0
    for i, target in enumerate(coarse_min):
        if target < level:
            level = target          # instant attack
        else:
            level = target + release_coeff * (level - target)
        smooth[i] = level
    gain = np.interp(np.arange(len(needed_gain)),
                     np.arange(n_blocks) * block + block / 2, smooth)
    out = samples * gain.astype(np.float32)
    return np.clip(out, -ceiling, ceiling).astype(np.float32)


def make_up_gain(samples: np.ndarray, target_peak: float = 0.89) -> np.ndarray:
    """Scale so the absolute peak equals *target_peak* (linear)."""
    peak = float(np.max(np.abs(samples))) if len(samples) else 0.0
    if peak <= 1e-9:
        return samples.astype(np.float32)
    return (samples * (target_peak / peak)).astype(np.float32)


_ = _linear_to_db
