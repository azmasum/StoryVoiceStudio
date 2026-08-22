"""Storytelling presets controlling voice style, pace, pauses and music."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryPreset:
    key: str
    label: str
    description: str
    wpm: int
    emotion_intensity: float
    pause_scale: float          # multiplies explicit/computed pauses
    voice_style_hint: str       # preferred voice catalog style tag
    music_mood: str             # suggested background music category
    music_gain_db: float
    ducking_db: float
    loudness_preset: str


PRESETS: dict[str, StoryPreset] = {
    "DOCUMENTARY": StoryPreset(
        "DOCUMENTARY", "Documentary",
        "Measured, authoritative narration with steady pacing.",
        150, 0.5, 1.0, "documentary", "Documentary", -20.0, 9.0, "YouTube",
    ),
    "HORROR": StoryPreset(
        "HORROR", "Horror",
        "Slow intimate delivery, controlled fear, long pauses.",
        145, 0.85, 1.6, "horror", "Dark", -22.0, 11.0, "YouTube",
    ),
    "MYSTERY": StoryPreset(
        "MYSTERY", "Mystery",
        "Quiet tension with deliberate pacing and intrigue.",
        148, 0.7, 1.4, "mystery", "Mystery", -21.0, 10.0, "YouTube",
    ),
    "TRUE_CRIME": StoryPreset(
        "TRUE_CRIME", "True Crime",
        "Serious, factual tone with suspenseful beats.",
        150, 0.65, 1.3, "serious", "Mystery", -20.0, 10.0, "YouTube",
    ),
    "EMOTIONAL": StoryPreset(
        "EMOTIONAL", "Emotional",
        "Warm, empathetic delivery with gentle dynamics.",
        152, 0.75, 1.2, "warm", "Emotional", -20.0, 9.0, "YouTube",
    ),
    "MOTIVATIONAL": StoryPreset(
        "MOTIVATIONAL", "Motivational",
        "Energetic, rising intensity toward a strong close.",
        162, 0.8, 0.9, "cinematic", "Inspirational", -19.0, 8.0, "YouTube",
    ),
    "ROMANCE": StoryPreset(
        "ROMANCE", "Romance",
        "Soft, warm and unhurried narration.",
        150, 0.7, 1.25, "warm", "Calm", -20.0, 9.0, "YouTube",
    ),
    "SCI_FI": StoryPreset(
        "SCI_FI", "Sci-Fi",
        "Cool, precise narration with cinematic weight.",
        155, 0.7, 1.15, "cinematic", "Dramatic", -20.0, 9.0, "YouTube",
    ),
    "HISTORICAL": StoryPreset(
        "HISTORICAL", "Historical",
        "Classic documentary gravitas.",
        148, 0.55, 1.1, "documentary", "Documentary", -20.0, 9.0, "YouTube",
    ),
    "BEDTIME": StoryPreset(
        "BEDTIME", "Bedtime",
        "Very calm, soft and slow for relaxation.",
        132, 0.45, 1.7, "calm", "Calm", -23.0, 12.0, "Podcast",
    ),
    "DARK_STORY": StoryPreset(
        "DARK_STORY", "Dark Story",
        "Grim, heavy atmosphere without theatrical excess.",
        143, 0.8, 1.5, "deep", "Dark", -22.0, 11.0, "YouTube",
    ),
    "CINEMATIC": StoryPreset(
        "CINEMATIC", "Cinematic",
        "Dynamic narration, dramatic pauses, strong climax.",
        153, 0.85, 1.35, "cinematic", "Cinematic", -19.0, 9.0, "YouTube",
    ),
}

DEFAULT_PRESET = "DOCUMENTARY"


def get_preset(key: str) -> StoryPreset:
    return PRESETS.get(key.upper().replace("-", "_"), PRESETS[DEFAULT_PRESET])


def preset_names() -> list[str]:
    return [p.key for p in PRESETS.values()]
