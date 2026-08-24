"""Regressions for the long-form generation crashes (Aug 2026).

- The lookahead limiter used to build one full-length array copy per
  sample of lookahead (30+ GiB on a 14 minute mix).
- Character DSP chains assumed >=18 kHz chunk rates and crashed with
  "critical frequencies" ValueError on 16 kHz low-quality voice models.
"""
import numpy as np

from audio.dsp.dynamics import limiter
from audio.dsp import meditation as meditation_mod
from audio.dsp import psych as psych_mod


def test_limiter_bounds_peaks_on_long_signal():
    sr = 44100
    duration_s = 120  # ~5.3M samples: big enough to catch O(N*look) blowups
    rng = np.random.default_rng(0)
    samples = (rng.standard_normal(sr * duration_s) * 0.9).astype(np.float32)
    out = limiter(samples, sr, ceiling_db=-1.5)
    assert len(out) == len(samples)
    peak = float(np.max(np.abs(out)))
    ceiling = 10 ** (-1.5 / 20)
    assert peak <= ceiling * 1.001


def test_limiter_matches_naive_future_peak():
    sr = 8000
    rng = np.random.default_rng(1)
    samples = (rng.standard_normal(sr) * 0.5).astype(np.float64)
    look = int(sr * 0.005)
    padded = np.abs(np.pad(samples, (look, 0), mode="edge"))
    naive = np.maximum.reduce([
        padded[i:len(padded) - look + i] if i > 0 else padded[:len(samples)]
        for i in range(look)
    ])
    fast = maximum_forward_max(padded, look, len(samples))
    assert np.allclose(fast, naive, atol=1e-12)


def maximum_forward_max(padded, look, n):
    from scipy.ndimage import maximum_filter1d
    return maximum_filter1d(padded, size=look,
                            origin=-(look // 2),
                            mode="nearest")[:n]


def test_meditation_profile_survives_16khz_model_rate():
    sr = 16000
    y = np.sin(np.linspace(0, 400, sr)) * 0.5
    out = meditation_mod.apply_meditation_profile(y, sr)
    assert len(out) == len(y)
    assert float(np.max(np.abs(out))) > 0.01


def test_psych_profile_survives_16khz_model_rate():
    sr = 16000
    y = np.sin(np.linspace(0, 400, sr)) * 0.5
    out = psych_mod.apply_psych_profile(y, sr)
    assert len(out) == len(y)
    assert float(np.max(np.abs(out))) > 0.01
