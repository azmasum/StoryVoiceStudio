"""Voice catalog - the 30 Gemini prebuilt studio voices.

Kept as the single import point (``tts.voices.catalog``) so existing
imports keep working; the data lives in gemini_catalog.py.
"""
from __future__ import annotations

from tts.base import VoiceInfo
from tts.voices.gemini_catalog import (
    CATALOG_VOICES,
    DEFAULT_DIALOGUE,
    DEFAULT_MODEL,
    DEFAULT_NARRATOR,
    GEMINI_MODELS,
    get_voice,
    voice_names,
)

HF_BASE = ""
HF_BASE_MAIN = ""


def model_urls(voice_id: str) -> tuple[str, str] | None:
    """Cloud voices have no files to download."""
    return None


def get_speakers(voice_id: str) -> tuple[tuple[str, int], ...] | None:
    return None


def find_by_style(style: str, gender: str | None = None) -> str | None:
    from tts.voices.gemini_catalog import find_by_style as _find

    return _find(style, gender)


def get_engine(voice_id: str) -> str:
    return "gemini"


__all__ = [
    "CATALOG_VOICES",
    "DEFAULT_DIALOGUE",
    "DEFAULT_MODEL",
    "DEFAULT_NARRATOR",
    "GEMINI_MODELS",
    "find_by_style",
    "get_engine",
    "get_speakers",
    "get_voice",
    "model_urls",
    "voice_names",
]
