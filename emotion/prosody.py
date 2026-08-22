"""Prosody planning: convert emotion/preset into concrete TTS parameters.

The planner produces engine-neutral parameters (rate scale, pause seconds,
intensity). Piper consumes the rate scale as ``length_scale``; other engines
map these values onto their own controls. Pitch/energy hints are reserved
for engines that support them - never faked on engines that do not.
"""
from __future__ import annotations

from dataclasses import dataclass

from emotion.presets import StoryPreset

# Emotion -> engine-neutral prosody profile.
# rate_scale > 1 means SLOWER speech (Piper length_scale semantics).
@dataclass(frozen=True)
class EmotionProfile:
    rate_scale: float
    pause_scale: float
    intensity: float      # how strongly the engine should express emotion
    pitch_shift_semitones: float = 0.0  # only used by engines with pitch control


EMOTION_PROFILES: dict[str, EmotionProfile] = {
    "CALM":       EmotionProfile(1.08, 1.3, 0.4),
    "HAPPY":      EmotionProfile(0.94, 0.8, 0.7),
    "SAD":        EmotionProfile(1.12, 1.5, 0.8),
    "FEAR":       EmotionProfile(1.05, 1.6, 0.9),
    "HORROR":     EmotionProfile(1.14, 1.8, 0.85),
    "SUSPENSE":   EmotionProfile(1.10, 1.7, 0.8),
    "EXCITED":    EmotionProfile(0.90, 0.7, 0.85),
    "ANGRY":      EmotionProfile(0.95, 0.9, 0.9),
    "SURPRISE":   EmotionProfile(0.96, 1.0, 0.75),
    "ROMANTIC":   EmotionProfile(1.06, 1.35, 0.65),
    "MYSTERIOUS": EmotionProfile(1.10, 1.55, 0.75),
    "SERIOUS":    EmotionProfile(1.04, 1.15, 0.5),
    "HOPEFUL":    EmotionProfile(1.00, 1.05, 0.6),
    "DRAMATIC":   EmotionProfile(1.02, 1.45, 0.9),
    "WHISPER":    EmotionProfile(1.16, 1.6, 0.7, pitch_shift_semitones=-1.5),
    "NEUTRAL":    EmotionProfile(1.00, 1.00, 0.0),
}


@dataclass
class ProsodyPlan:
    length_scale: float          # direct TTS speed factor (1.0 = natural)
    pause_before: float          # seconds of silence inserted before audio
    pause_after: float           # seconds after
    intensity: float             # emotional strength 0..1 (engine-dependent)
    emotion: str
    effects: tuple[str, ...]
    pitch_shift_semitones: float = 0.0


def plan_prosody(
    emotion: str,
    effects: tuple[str, ...] | frozenset[str] = (),
    pause_before: float = 0.0,
    pause_after: float = 0.0,
    preset: StoryPreset | None = None,
    global_intensity: float = 0.7,
) -> ProsodyPlan:
    """Build a concrete plan; safe fallbacks when an effect is unsupported."""
    profile = EMOTION_PROFILES.get(emotion.upper(), EMOTION_PROFILES["NEUTRAL"])
    preset_scale = preset.pause_scale if preset else 1.0
    strength = max(0.0, min(1.0, global_intensity))

    # Blend toward neutral as user intensity drops (never fully robotic).
    blended_rate = 1.0 + (profile.rate_scale - 1.0) * strength
    blended_pause = profile.pause_scale * preset_scale
    intensity = profile.intensity * strength

    effect_set = set(effects)
    if "whisper" in effect_set:
        blended_rate *= 1.05
        intensity = max(intensity, 0.6)

    return ProsodyPlan(
        length_scale=round(blended_rate, 4),
        pause_before=round(pause_before * blended_pause, 3),
        pause_after=round(pause_after * blended_pause, 3),
        intensity=round(intensity, 3),
        emotion=emotion.upper(),
        effects=tuple(sorted(effect_set)),
        pitch_shift_semitones=profile.pitch_shift_semitones * strength,
    )


def wpm_to_length_scale(natural_wpm: float, target_wpm: int) -> float:
    """Convert a words-per-minute target into a Piper-style length scale."""
    if natural_wpm <= 0 or target_wpm <= 0:
        return 1.0
    return round(max(0.5, min(2.5, natural_wpm / target_wpm)), 4)
