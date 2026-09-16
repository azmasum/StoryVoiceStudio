"""Emotion engine: presets, rule-based analysis and prosody planning."""
from emotion.analyzer import (
    EMOTIONS,
    SentenceAnalysis,
    analyze_sentence,
    annotate_script,
    detect_dialogues,
    detect_story_structure,
)
from emotion.presets import PRESETS, DEFAULT_PRESET, StoryPreset, get_preset, preset_names
from emotion.prosody import (
    EMOTION_PROFILES,
    LENGTH_SCALE_MAX,
    LENGTH_SCALE_MIN,
    ProsodyPlan,
    clamp_length_scale,
    plan_prosody,
    wpm_to_length_scale,
)

__all__ = [
    "EMOTIONS",
    "SentenceAnalysis",
    "analyze_sentence",
    "annotate_script",
    "detect_dialogues",
    "detect_story_structure",
    "PRESETS",
    "DEFAULT_PRESET",
    "StoryPreset",
    "get_preset",
    "preset_names",
    "EMOTION_PROFILES",
    "LENGTH_SCALE_MAX",
    "LENGTH_SCALE_MIN",
    "ProsodyPlan",
    "clamp_length_scale",
    "plan_prosody",
    "wpm_to_length_scale",
]
