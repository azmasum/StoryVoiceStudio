"""Psychology-explainer voice character DSP - the approved v11 recipe.

Deep-warm intelligent narrator: -1.5 semitone pitch, near-natural 0.95x
pace, high clarity (highs preserved), dry authoritative room, gentle glue
compression at medium energy. Surprising-fact lines can opt into a
briefly deeper/slower delivery.
"""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt, tf2sos

PITCH_FACTOR = 2 ** (-1.5 / 12)   # about -1.5 semitones
DEEP_PITCH_FACTOR = 2 ** (-1.9 / 12)
SPEED_FACTOR = 0.95               # near natural pace
LENGTH_SCALE_MULTIPLIER = SPEED_FACTOR * PITCH_FACTOR       # ~0.87
RESAMPLE_UP = 1000

PEAK_F0 = 180
PEAK_DB = 2.0                     # deep-warm without radio boom
LOWPASS_HZ = 9000                 # clarity stays high
REVERB_TAIL = 0.25                # dry-ish authority
REVERB_WET = 0.05


def pitch_shift_slow(y: np.ndarray, deep: bool = False) -> np.ndarray:
    """Lower pitch ~1.5 semitones (or more when *deep*) and stretch time."""
    factor = DEEP_PITCH_FACTOR if deep else PITCH_FACTOR
    return resample_poly(y, RESAMPLE_UP, int(round(RESAMPLE_UP / factor)))


def _peaking(y: np.ndarray, sr: int) -> np.ndarray:
    w0 = 2 * np.pi * PEAK_F0 / sr
    amp = 10 ** (PEAK_DB / 40)
    alpha = np.sin(w0) / (2 * 0.8)
    b = np.array([1 + alpha * amp, -2 * np.cos(w0), 1 - alpha * amp])
    a = np.array([1 + alpha / amp, -2 * np.cos(w0), 1 - alpha / amp])
    return sosfilt(tf2sos(b, a), y)


def apply_psych_profile(y: np.ndarray, sr: int,
                        final_line: bool = False) -> np.ndarray:
    y = sosfilt(butter(2, 70, "high", fs=sr, output="sos"), y)
    y = _peaking(y, sr)
    y = sosfilt(butter(2, LOWPASS_HZ, "low", fs=sr, output="sos"), y)

    n = max(int(sr * REVERB_TAIL), 8)
    t = np.linspace(0, REVERB_TAIL, n)
    ir = np.random.default_rng(3).standard_normal(n) * np.exp(-6.9 * t / REVERB_TAIL)
    ir = sosfilt(butter(2, 4000, "low", fs=sr, output="sos"), ir)
    peak = float(np.max(np.abs(ir))) or 1.0
    ir /= peak
    y = (1 - REVERB_WET) * y + REVERB_WET * fftconvolve(y, ir)[: len(y)]

    y = np.tanh(1.2 * y) / np.tanh(1.2)

    if final_line:
        fade_n = min(int(sr * 0.30), max(0, len(y) - 1))
        if fade_n:
            y[-fade_n:] *= np.linspace(1.0, 0.80, fade_n)

    out_peak = float(np.max(np.abs(y))) or 1.0
    return y / out_peak * 0.88
