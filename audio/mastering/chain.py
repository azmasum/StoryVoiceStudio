"""Mastering presets and the full processing chain."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from audio.dsp.dynamics import compressor, limiter
from audio.dsp.filters import de_esser, high_pass, tilt_eq
from audio.dsp.loudness import normalize_to_lufs


@dataclass(frozen=True)
class LoudnessPreset:
    key: str
    target_lufs: float
    ceiling_dbtp: float
    description: str


LOUDNESS_PRESETS: dict[str, LoudnessPreset] = {
    "YouTube": LoudnessPreset("YouTube", -14.0, -1.0,
                              "Standard for YouTube storytelling channels."),
    "Podcast": LoudnessPreset("Podcast", -16.0, -1.5,
                              "Common podcast platforms target."),
    "Audiobook": LoudnessPreset("Audiobook", -18.0, -3.0,
                                "ACX-style conservative mastering."),
    "Cinematic": LoudnessPreset("Cinematic", -16.0, -1.5,
                                "More dynamic range, gentle ceiling."),
}


def get_preset(key: str) -> LoudnessPreset:
    return LOUDNESS_PRESETS.get(key, LOUDNESS_PRESETS["YouTube"])


@dataclass
class MasteringSettings:
    preset: str = "YouTube"
    custom_lufs: float | None = None   # when set, overrides preset target
    high_pass_hz: float = 75.0
    de_ess_db: float = -3.0
    compress_threshold_db: float = -22.0
    compress_ratio: float = 2.8
    enable_saturation: bool = True

    def target(self) -> tuple[float, float]:
        preset = get_preset(self.preset)
        lufs = self.custom_lufs if self.custom_lufs is not None else preset.target_lufs
        return lufs, preset.ceiling_dbtp


def _subtle_saturation(samples: np.ndarray, drive: float = 1.15) -> np.ndarray:
    """Very light tanh saturation for glue/warmth (kept subtle on purpose)."""
    return np.tanh(samples * drive) / np.tanh(drive)


def master_voice(samples: np.ndarray, sample_rate: int,
                 settings: MasteringSettings | None = None) -> tuple[np.ndarray, dict]:
    """Full narration mastering chain.

    Noise Reduction -> High-pass -> EQ -> De-esser -> Compression ->
    Subtle Saturation -> Limiter -> Loudness Normalization.
    """
    settings = settings or MasteringSettings()
    audio = np.asarray(samples, dtype=np.float32)

    # Noise reduction: high-pass handles broadband rumble; a spectral gate
    # would need a noise profile, which is intentionally not faked here.
    audio = high_pass(audio, sample_rate, settings.high_pass_hz)
    audio = tilt_eq(audio, sample_rate)
    if abs(settings.de_ess_db) > 0.01:
        audio = de_esser(audio, sample_rate, reduction_db=settings.de_ess_db)
    audio = compressor(
        audio, sample_rate,
        threshold_db=settings.compress_threshold_db,
        ratio=settings.compress_ratio,
    )
    if settings.enable_saturation:
        audio = _subtle_saturation(audio)
    audio = limiter(audio, sample_rate, ceiling_db=-1.6)

    target_lufs, ceiling = settings.target()
    audio, stats = normalize_to_lufs(audio, sample_rate, target_lufs, ceiling)
    return audio.astype(np.float32), stats


def master_mix(samples: np.ndarray, sample_rate: int,
               settings: MasteringSettings | None = None) -> tuple[np.ndarray, dict]:
    """Final mixdown bus processing: gentle compression + loudness only."""
    settings = settings or MasteringSettings()
    audio = np.asarray(samples, dtype=np.float32)
    audio = compressor(audio, sample_rate, threshold_db=-16.0, ratio=1.6,
                       attack_ms=25.0, release_ms=250.0)
    audio = limiter(audio, sample_rate, ceiling_db=-1.4)
    target_lufs, ceiling = settings.target()
    audio, stats = normalize_to_lufs(audio, sample_rate, target_lufs, ceiling)
    return audio.astype(np.float32), stats


__all__ = [
    "LoudnessPreset",
    "LOUDNESS_PRESETS",
    "get_preset",
    "MasteringSettings",
    "master_voice",
    "master_mix",
]
