"""Meditation voice preset DSP - the approved v10 recipe.

Warm proximity EQ, soft highs, near-dry intimate room, gentle glue
compression and a soft limiter. Applied per synthesized chunk so the
chunk cache stores the final sound.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt, tf2sos

PITCH_FACTOR = 2 ** (-1.3 / 12)   # about -1.3 semitones
SPEED_FACTOR = 0.85               # final playback speed vs natural pacing
LENGTH_SCALE_MULTIPLIER = SPEED_FACTOR ** -1 * PITCH_FACTOR  # 1.069
RESAMPLE_UP = 1000
RESAMPLE_DOWN = int(round(1000 / PITCH_FACTOR))             # 1100 -> pitch down

_PEAK_F0 = 190
_PEAK_DB = 3.5
_LOWPASS_HZ = 5200
_REVERB_TAIL = 0.32
_REVERB_WET = 0.08


def _peaking(y: np.ndarray, sr: int) -> np.ndarray:
    w0 = 2 * np.pi * _PEAK_F0 / sr
    amp = 10 ** (_PEAK_DB / 40)
    alpha = np.sin(w0) / (2 * 0.8)
    b = np.array([1 + alpha * amp, -2 * np.cos(w0), 1 - alpha * amp])
    a = np.array([1 + alpha / amp, -2 * np.cos(w0), 1 - alpha / amp])
    return sosfilt(tf2sos(b, a), y)


def pitch_shift_slow(y: np.ndarray) -> np.ndarray:
    """Lower pitch ~1.3 semitones and stretch time by 1/PITCH_FACTOR."""
    return resample_poly(y, RESAMPLE_UP, RESAMPLE_DOWN)


def _safe_lp(y: np.ndarray, sr: int, hz: float) -> np.ndarray:
    """Lowpass with Wn clamped under Nyquist (16 kHz voice models exist)."""
    return sosfilt(butter(2, min(hz, sr * 0.45), "low", fs=sr,
                          output="sos"), y)


def apply_meditation_profile(y: np.ndarray, sr: int) -> np.ndarray:
    """Post chain from the approved audition sample (v10)."""
    y = sosfilt(butter(2, 60, "high", fs=sr, output="sos"), y)
    y = _peaking(y, sr)
    y = _safe_lp(y, sr, _LOWPASS_HZ)

    n = max(int(sr * _REVERB_TAIL), 8)
    t = np.linspace(0, _REVERB_TAIL, n)
    rng = np.random.default_rng(11)
    ir = rng.standard_normal(n) * np.exp(-6.9 * t / _REVERB_TAIL)
    ir = sosfilt(butter(2, 3500, "low", fs=sr, output="sos"), ir)
    peak = float(np.max(np.abs(ir))) or 1.0
    ir /= peak
    y = (1 - _REVERB_WET) * y + _REVERB_WET * fftconvolve(y, ir)[: len(y)]

    y = np.tanh(1.15 * y) / np.tanh(1.15)

    fade_n = min(int(sr * 0.22), max(0, len(y) - 1))
    if fade_n:
        y[-fade_n:] *= np.linspace(1.0, 0.82, fade_n)

    out_peak = float(np.max(np.abs(y))) or 1.0
    return y / out_peak * 0.85
