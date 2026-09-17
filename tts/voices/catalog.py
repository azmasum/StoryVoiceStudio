"""Piper voice catalog (US-English + Bengali).

All voices ship from the rhasspy/piper-voices repository (MIT license).
License facts are taken from the repository itself - never fabricated.
Download URLs point to the official Hugging Face mirror of that repo.
"""
from __future__ import annotations

from tts.base import VoiceInfo

HF_BASE = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US"
)
HF_BASE_MAIN = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/main"
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
    "en_US-lessac-high": {
        "subpath": "lessac/high",
        "gender": "female",
        "style": "warm",
        "name": "Lessac (High)",
        "size_mb": 115.0,
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
    # Multi-speaker Bengali voice (16 speakers, male & female).
    # Added upstream after the v1.0.0 release, so it is fetched from the
    # repository's main branch. Speaker names are opaque dataset IDs
    # (OpenSLR 37 / CMU Indic); audition to find preferred voices.
    "bn_BD-google-medium": {
        "subpath": "bn/bn_BD/google/medium",
        "base": HF_BASE_MAIN,
        "gender": "male+female",
        "style": "multilingual",
        "name": "Bengali Multi (Medium)",
        "size_mb": 74.0,
        "accent": "bn-BD",
        "license": "MIT (rhasspy/piper-voices); training data CC-BY-SA 4.0 "
                   "+ CMU license - attribution required for redistribution",
        "speakers": [
            ("00737", 0), ("01232", 1), ("02194", 2), ("03042", 3),
            ("00779", 4), ("01701", 5), ("0834", 6), ("1010", 7),
            ("3108", 8), ("3713", 9), ("3958", 10), ("4046", 11),
            ("4811", 12), ("5958", 13), ("9169", 14), ("rm", 15),
        ],
    },
    # Transformer voices (Indic Parler-TTS, Apache-2.0). One shared
    # checkpoint serves many voices via description prompts; files are
    # downloaded on demand into models/parler (NOT bundled - ~4 GB).
    # The upstream repo is access-gated: users accept the license on
    # Hugging Face and paste a read token into the Model Manager.
    "parler-bn-female": {
        "engine": "parler",
        "repo": "ai4bharat/indic-parler-tts",
        "gender": "female",
        "style": "storytelling",
        "name": "Parler Bengali Female (Beta)",
        "size_mb": 3800.0,
        "accent": "bn-BD",
        "license": "Apache-2.0 (ai4bharat/indic-parler-tts)",
        "sample_rate": 44100,
    },
    "parler-bn-male": {
        "engine": "parler",
        "repo": "ai4bharat/indic-parler-tts",
        "gender": "male",
        "style": "storytelling",
        "name": "Parler Bengali Male (Beta)",
        "size_mb": 3800.0,
        "accent": "bn-BD",
        "license": "Apache-2.0 (ai4bharat/indic-parler-tts)",
        "sample_rate": 44100,
    },
}

CATALOG_VOICES: list[dict] = []
for _vid, _meta in _CATALOG.items():
    _entry = {
        "voice_id": _vid,
        "name": _meta["name"],
        "gender": _meta["gender"],
        "accent": _meta.get("accent", "en-US"),
        "language": _meta.get("accent", "en-US"),
        "style": _meta["style"],
        "license": _meta.get(
            "license", "MIT (rhasspy/piper-voices)"),
        "commercial_use": True,
        "model_size_mb": _meta["size_mb"],
        "engine": _meta.get("engine", "piper"),
        "sample_rate": int(_meta.get("sample_rate", 22050)),
    }
    if "speakers" in _meta:
        _entry["speakers"] = tuple(_meta["speakers"])
    CATALOG_VOICES.append(_entry)


def model_urls(voice_id: str) -> tuple[str, str] | None:
    """Return (onnx_url, json_url) for a catalog voice.

    Returns None for non-Piper voices (their files are fetched by the
    engine-specific installer instead).
    """
    meta = _CATALOG.get(voice_id)
    if not meta or meta.get("engine", "piper") != "piper":
        return None
    base = f"{meta.get('base', HF_BASE)}/{meta['subpath']}/{voice_id}"
    return f"{base}.onnx", f"{base}.onnx.json"


def parler_repo(voice_id: str) -> str | None:
    """Hugging Face repo for a Parler voice, or None."""
    meta = _CATALOG.get(voice_id)
    if not meta or meta.get("engine") != "parler":
        return None
    return str(meta.get("repo", "")) or None


def get_speakers(voice_id: str) -> tuple[tuple[str, int], ...] | None:
    """Speaker list for multi-speaker voices; None otherwise."""
    meta = _CATALOG.get(voice_id)
    if not meta:
        return None
    speakers = meta.get("speakers")
    return tuple(speakers) if speakers else None


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
