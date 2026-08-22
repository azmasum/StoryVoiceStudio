"""Frequency-domain filters (biquad implementations via scipy)."""
from __future__ import annotations

import numpy as np
from scipy.signal import bilinear, lfilter, sosfilt, zpk2sos


def high_pass(samples: np.ndarray, sample_rate: int,
              cutoff_hz: float = 80.0) -> np.ndarray:
    """Remove rumble below *cutoff_hz* (8th-order Butterworth)."""
    from scipy.signal import butter

    sos = butter(8, cutoff_hz / (sample_rate / 2), btype="highpass",
                 output="sos")
    return sosfilt(sos, samples).astype(np.float32)


def low_pass(samples: np.ndarray, sample_rate: int,
             cutoff_hz: float = 16000.0) -> np.ndarray:
    from scipy.signal import butter

    sos = butter(4, min(cutoff_hz, sample_rate / 2 - 100) / (sample_rate / 2),
                 btype="lowpass", output="sos")
    return sosfilt(sos, samples).astype(np.float32)


def _peaking_filter(sample_rate: int, freq_hz: float, gain_db: float,
                    q: float = 0.9) -> tuple[np.ndarray, np.ndarray]:
    """RBJ peaking EQ biquad coefficients."""
    a_gain = 10 ** (gain_db / 40.0)
    w0 = 2 * np.pi * freq_hz / sample_rate
    alpha = np.sin(w0) / (2 * q)
    b0 = 1 + alpha * a_gain
    b1 = -2 * np.cos(w0)
    b2 = 1 - alpha * a_gain
    a0 = 1 + alpha / a_gain
    a1 = -2 * np.cos(w0)
    a2 = 1 - alpha / a_gain
    return (
        np.array([b0 / a0, b1 / a0, b2 / a0]),
        np.array([1.0, a1 / a0, a2 / a0]),
    )


def tilt_eq(samples: np.ndarray, sample_rate: int,
            low_gain_db: float = 1.5, high_cut_hz: float = 3200.0,
            high_gain_db: float = 1.0) -> np.ndarray:
    """Gentle broadcast-style EQ: small warmth lift and presence shelf."""
    out = samples
    for freq, gain in ((180.0, low_gain_db), (high_cut_hz, high_gain_db)):
        b, a = _peaking_filter(sample_rate, freq, gain)
        out = lfilter(b, a, out)
    return out.astype(np.float32)


def de_esser(samples: np.ndarray, sample_rate: int,
             center_hz: float = 6500.0, reduction_db: float = -3.0) -> np.ndarray:
    """Static sibilance taming dip around *center_hz*.

    A full dynamic de-esser is future work; this gentle static dip keeps
    harsh S sounds under control without audible artifacts.
    """
    b, a = _peaking_filter(sample_rate, center_hz, reduction_db, q=1.2)
    return lfilter(b, a, samples).astype(np.float32)


def envelope_follow(samples: np.ndarray, sample_rate: int,
                    attack_ms: float, release_ms: float) -> np.ndarray:
    """Smoothed absolute envelope with asymmetric attack/release."""
    rectified = np.abs(samples).astype(np.float64)
    block = max(1, int(sample_rate * 0.005))
    n_blocks = len(rectified) // block + (len(rectified) % block != 0)
    coarse = np.array([
        rectified[i * block:(i + 1) * block].max() if len(rectified[i * block:(i + 1) * block]) else 0.0
        for i in range(n_blocks)
    ])
    attack_coeff = float(np.exp(-block / max(1e-6, sample_rate * attack_ms / 1000.0)))
    release_coeff = float(np.exp(-block / max(1e-6, sample_rate * release_ms / 1000.0)))
    smoothed = np.zeros_like(coarse)
    level = 0.0
    for i, value in enumerate(coarse):
        coeff = attack_coeff if value < level else release_coeff
        level = value + coeff * (level - value)
        smoothed[i] = level
    expanded = np.interp(
        np.arange(len(rectified)),
        np.arange(n_blocks) * block + block / 2,
        smoothed,
    )
    return expanded.astype(np.float32)


_ = bilinear, zpk2sos  # reserved for future filter designs
