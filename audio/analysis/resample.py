"""High-quality resampling via scipy's polyphase method."""
from __future__ import annotations

import numpy as np
from scipy.signal import resample_poly
from math import gcd


def resample_to(samples: np.ndarray, source_rate: int,
                target_rate: int) -> np.ndarray:
    if source_rate == target_rate or len(samples) == 0:
        return samples.astype(np.float32)
    divisor = gcd(int(source_rate), int(target_rate))
    up = target_rate // divisor
    down = source_rate // divisor
    out = resample_poly(np.asarray(samples, dtype=np.float64), up, down)
    return out.astype(np.float32)
