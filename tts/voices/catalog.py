"""Voice catalog - EdgeTTS (free) + Gemini (cloud) voices.

Single import point (``tts.voices.catalog``); per-engine data lives in
edge_catalog.py / gemini_catalog.py.
"""
from __future__ import annotations

from tts.base import VoiceInfo
from tts.voices import edge_catalog, gemini_catalog

CATALOG_VOICES: list[dict] = (
    list(edge_catalog.CATALOG_VOICES) + list(gemini_catalog.CATALOG_VOICES)
)

HF_BASE = ""
HF_BASE_MAIN = ""


def model_urls(voice_id: str) -> tuple[str, str] | None:
    """Cloud voices have no files to download."""
    return None


def get_speakers(voice_id: str) -> tuple[tuple[str, int], ...] | None:
    return None


def get_voice(voice_id: str) -> VoiceInfo | None:
    return edge_catalog.get_voice(voice_id) or gemini_catalog.get_voice(voice_id)


def get_engine(voice_id: str) -> str:
    if edge_catalog.get_voice(voice_id) is not None:
        return "edge"
    return "gemini"


def voices_for_engine(engine: str) -> list[dict]:
    return [e for e in CATALOG_VOICES if e.get("engine") == engine]


def find_by_style(style: str, gender: str | None = None) -> str | None:
    for entry in CATALOG_VOICES:
        if entry["style"].lower() == style.lower() and (
                gender is None or entry["gender"] == gender):
            return entry["voice_id"]
    return None


def voice_names() -> list[str]:
    return [entry["voice_id"] for entry in CATALOG_VOICES]


__all__ = [
    "CATALOG_VOICES",
    "find_by_style",
    "get_engine",
    "get_speakers",
    "get_voice",
    "model_urls",
    "voice_names",
    "voices_for_engine",
]
