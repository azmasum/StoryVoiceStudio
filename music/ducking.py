"""Music ducking: sidechain-style envelope automation.

While the voice is active, music gain is lowered by *ducking_db*, then
gently restored with configurable attack/release times.
"""
from __future__ import annotations

import numpy as np

from audio.dsp.filters import envelope_follow


def duck_music(
    music: np.ndarray,
    voice_envelope_ref: np.ndarray,
    sample_rate: int,
    depth_db: float = 9.0,
    attack_ms: float = 200.0,
    release_ms: float = 300.0,
) -> np.ndarray:
    """Duck *music* using the voice activity of *voice_envelope_ref*.

    Both arrays are placed on a common timeline starting at t=0; the voice
    reference must already be zero-padded to its timeline position.
    """
    n = len(music)
    if n == 0 or len(voice_envelope_ref) == 0:
        return music.astype(np.float32)

    env = envelope_follow(np.asarray(voice_envelope_ref, dtype=np.float32),
                          sample_rate, 30.0, 150.0)
    if len(env) < n:
        env = np.pad(env, (0, n - len(env)))
    else:
        env = env[:n]

    threshold = float(env.max()) * 0.06 if env.size else 0.0
    active = env > max(threshold, 1e-6)

    # Build target gain curve: ducked while voice is active.
    ducked = 10 ** (-abs(depth_db) / 20.0)
    target = np.where(active, ducked, 1.0)

    # Smooth with asymmetric time constants (attack when ducking starts).
    block = max(1, int(sample_rate * 0.01))
    pad = (-len(target)) % block
    if pad:
        target = np.pad(target, (0, pad), mode="edge")
    coarse = target.reshape(-1, block).mean(axis=1)
    atk = float(np.exp(-block / max(1e-6, sample_rate * attack_ms / 1000.0)))
    rel = float(np.exp(-block / max(1e-6, sample_rate * release_ms / 1000.0)))

    smooth = np.zeros_like(coarse)
    level = 1.0
    for i, wanted in enumerate(coarse):
        coeff = atk if wanted < level else rel
        level = wanted + coeff * (level - wanted)
        smooth[i] = level

    gain = np.interp(np.arange(n), np.arange(len(smooth)) * block + block / 2,
                     smooth).astype(np.float32)[:n]
    return (music * gain).astype(np.float32)


def compute_ducking_gain_curve(
    length_samples: int,
    voice_activity: np.ndarray,
    sample_rate: int,
    depth_db: float = 9.0,
    attack_ms: float = 200.0,
    release_ms: float = 300.0,
) -> np.ndarray:
    """Expose the raw gain curve for UI visualization."""
    fake_voice = np.where(voice_activity > 0, 1.0, 0.0)
    env = envelope_follow(fake_voice, sample_rate, 5.0, 20.0)[:length_samples]
    if len(env) < length_samples:
        env = np.pad(env, (0, length_samples - len(env)))
    ducked = 10 ** (-abs(depth_db) / 20.0)
    target = np.where(env > 0.3, ducked, 1.0)
    return target.astype(np.float32)
