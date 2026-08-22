"""US-English Piper voice catalog.

All voices ship from the rhasspy/piper-voices repository (MIT license).
License facts are taken from the repository itself - never fabricated.
Download URLs point to the official Hugging Face mirror of that repo.
"""
from __future__ import annotations

from tts.base import VoiceInfo

HF_BASE = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US"
)

# voice_id -> (subpath, gender, style, description)
_CATALOG: dict[str, dict] = {
    "en_US-lessac-medium": {
        "subpath": "lessac/medium",
        "gender": "female",
        "style": "warm",
        "name": "Lessac (Medium)",
        "size_mb": 63.0,
    },
    "en_US-amy-medium": {
        "subpath": "amy/medium",
        "gender": "female",
        "style": "calm",
        "name": "Amy (Medium)",
        "size_mb": 63.0,
    },
    "en_US-hfc_female-medium": {
        "subpath": "hfc_female/medium",
        "gender": "female",
        "style": "documentary",
        "name": "HFC Female (Medium)",
        "size_mb": 63.0,
    },
    "en_US-ryan-high": {
        "subpath": "ryan/high",
        "gender": "male",
        "style": "cinematic",
        "name": "Ryan (High)",
        "size_mb": 118.0,
    },
    "en_US-joe-medium": {
        "subpath": "joe/medium",
        "gender": "male",
        "style": "deep",
        "name": "Joe (Medium)",
        "size_mb": 63.0,
    },
    "en_US-kusal-medium": {
        "subpath": "kusal/medium",
        "gender": "male",
        "style": "serious",
        "name": "Kusal (Medium)",
        "size_mb": 63.0,
    },
    "en_US-danny-low": {
        "subpath": "danny/low",
        "gender": "male",
        "style": "mystery",
        "name": "Danny (Low)",
        "size_mb": 20.0,
    },
}

CATALOG_VOICES: list[dict] = [
    {
        "voice_id": vid,
        "name": meta["name"],
        "gender": meta["gender"],
        "accent": "en-US",
        "style": meta["style"],
        "license": "MIT (rhasspy/piper-voices)",
        "commercial_use": True,
        "model_size_mb": meta["size_mb"],
    }
    for vid, meta in _CATALOG.items()
]


def model_urls(voice_id: str) -> tuple[str, str] | None:
    """Return (onnx_url, json_url) for a catalog voice."""
    meta = _CATALOG.get(voice_id)
    if not meta:
        return None
    base = f"{HF_BASE}/{meta['subpath']}/{voice_id}"
    return f"{base}.onnx", f"{base}.onnx.json"


def get_voice(voice_id: str) -> VoiceInfo | None:
    for entry in CATALOG_VOICES:
        if entry["voice_id"] == voice_id:
            return VoiceInfo(**entry)
    return None


def find_by_style(style: str, gender: str | None = None) -> str | None:
    """Pick the first catalog voice matching a style hint."""
    for entry in CATALOG_VOICES:
        if entry["style"] == style and (gender is None or entry["gender"] == gender):
            return entry["voice_id"]
    return None
