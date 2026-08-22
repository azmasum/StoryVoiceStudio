"""Fade and crossfade utilities."""
from __future__ import annotations

import numpy as np


def apply_fade_in(samples: np.ndarray, sample_rate: int, seconds: float) -> np.ndarray:
    n = min(len(samples), int(sample_rate * seconds))
    if n <= 0:
        return samples
    out = samples.copy()
    curve = np.linspace(0.0, 1.0, n) ** 1.5
    out[:n] *= curve.astype(samples.dtype)
    return out


def apply_fade_out(samples: np.ndarray, sample_rate: int, seconds: float) -> np.ndarray:
    n = min(len(samples), int(sample_rate * seconds))
    if n <= 0:
        return samples
    out = samples.copy()
    curve = np.linspace(1.0, 0.0, n) ** 1.5
    out[-n:] *= curve.astype(samples.dtype)
    return out


def crossfade(a: np.ndarray, b: np.ndarray, sample_rate: int,
              seconds: float) -> np.ndarray:
    """Overlap two signals for *seconds* with equal-power crossfade."""
    n = min(len(a), len(b), int(sample_rate * seconds))
    if n <= 0:
        return np.concatenate([a, b])
    tail, head = a[-n:], b[:n]
    fade_out = np.cos(np.linspace(0, np.pi / 2, n)) ** 2
    fade_in = np.sin(np.linspace(0, np.pi / 2, n)) ** 2
    mixed = (tail * fade_out + head * fade_in).astype(np.float32)
    return np.concatenate([a[:-n], mixed, b[n:]])


def place_at(base: np.ndarray, overlay: np.ndarray, start_sample: int,
             gain_linear: float = 1.0) -> np.ndarray:
    """Mix *overlay* into *base* at *start_sample*, extending base if needed."""
    end = start_sample + len(overlay)
    if end > len(base):
        base = np.pad(base, (0, end - len(base)))
    segment = base[start_sample:end]
    base[start_sample:end] = segment + overlay[:len(segment)] * gain_linear
    return base
