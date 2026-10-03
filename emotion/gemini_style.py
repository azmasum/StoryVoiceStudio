"""Style instructions for Gemini TTS (natural-language control).

Gemini TTS is steered with plain-language directions prefixed to the text
("Read in a fearful whisper: ..."). This module converts the app's
emotion/preset system into those directions, in English (the control
language) regardless of the narration language.
"""
from __future__ import annotations

from emotion.analyzer import analyze_sentence
from emotion.prosody import EMOTION_PROFILES

# Emotion -> delivery direction.
EMOTION_STYLE: dict[str, str] = {
    "CALM": "in a calm, steady voice",
    "HAPPY": "cheerfully, with a bright smile in the voice",
    "SAD": "in a sad, heavy voice, slowly",
    "FEAR": "in a fearful, trembling voice",
    "HORROR": "in a dark, ominous whisper",
    "SUSPENSE": "in a tense, hushed voice, building suspense",
    "EXCITED": "with energetic excitement",
    "ANGRY": "in an angry, forceful voice",
    "SURPRISE": "with genuine surprise",
    "ROMANTIC": "in a warm, tender voice",
    "MYSTERIOUS": "in a mysterious, quiet voice",
    "SERIOUS": "in a serious, formal tone",
    "HOPEFUL": "in a hopeful, uplifting voice",
    "DRAMATIC": "with dramatic intensity",
    "WHISPER": "in a soft whisper",
    "NEUTRAL": "in a clear, natural storytelling voice",
}

# Preset -> global direction prepended once per generation.
PRESET_DIRECTION: dict[str, str] = {
    "DOCUMENTARY": "measured and authoritative",
    "HORROR": "slow and intimate, full of dread",
    "MYSTERY": "quiet and full of intrigue",
    "TRUE_CRIME": "serious and factual, with suspenseful beats",
    "EMOTIONAL": "warm and empathetic",
    "MOTIVATIONAL": "energetic, rising toward a strong close",
    "ROMANCE": "soft, warm and unhurried",
    "SCI_FI": "cool and precise, with cinematic weight",
    "HISTORICAL": "with classic documentary gravitas",
    "BEDTIME": "very calm, soft and slow, soothing",
    "DARK_STORY": "grim and heavy, without theatrical excess",
    "CINEMATIC": "dynamic, with dramatic pauses",
}


def pace_word(emotion: str, intensity: float = 0.7) -> str:
    """Pace hint derived from the emotion's rate profile."""
    profile = EMOTION_PROFILES.get(emotion.upper())
    if profile is None:
        return ""
    blended = 1.0 + (profile.rate_scale - 1.0) * max(0.0, min(1.0, intensity))
    if blended > 1.06:
        return "slowly"
    if blended < 0.94:
        return "quickly"
    return ""


def style_for_chunk(emotion: str, preset_key: str = "DOCUMENTARY",
                    intensity: float = 0.7) -> str:
    """Full style direction for one chunk (without the text)."""
    emo = (emotion or "NEUTRAL").upper()
    base = EMOTION_STYLE.get(emo, EMOTION_STYLE["NEUTRAL"])
    pace = pace_word(emo, intensity)
    direction = base if emo == "NEUTRAL" else base
    if pace and pace not in direction:
        direction = f"{direction}, {pace}"
    preset = PRESET_DIRECTION.get(preset_key, "")
    if preset and emo == "NEUTRAL":
        direction = f"{direction}, {preset}"
    return direction


def prompt_for_chunk(text: str, emotion: str = "NEUTRAL",
                     preset_key: str = "DOCUMENTARY",
                     intensity: float = 0.7) -> str:
    """Text sent to the API: style direction + the narration."""
    return f"Read aloud {style_for_chunk(emotion, preset_key, intensity)}: {text}"


def is_dialogue_chunk(text: str) -> bool:
    """True when a meaningful share of the chunk is spoken dialogue."""
    from emotion.analyzer import SENTENCE_SPLIT_RE

    sentences = [s for s in SENTENCE_SPLIT_RE.split(text) if s.strip()]
    if not sentences:
        return False
    hits = sum(1 for s in sentences if analyze_sentence(s).is_dialogue)
    return hits > 0 and hits / len(sentences) >= 0.4


__all__ = [
    "EMOTION_STYLE",
    "PRESET_DIRECTION",
    "is_dialogue_chunk",
    "pace_word",
    "prompt_for_chunk",
    "style_for_chunk",
]
