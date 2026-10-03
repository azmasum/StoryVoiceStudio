"""EdgeTTS voice catalog (Microsoft Edge online voices, keyless & free).

Verified live via `edge-tts --list-voices`. No download, no API key, no
billing - synthesis calls the Edge TTS endpoint (internet required).
"""
from __future__ import annotations

from tts.base import VoiceInfo

# (voice_id, gender, style, language label)
_VOICES: tuple[tuple[str, str, str, str], ...] = (
    ("en-US-AriaNeural", "female", "News/Novel", "en-US"),
    ("en-US-JennyNeural", "female", "General", "en-US"),
    ("en-US-EmmaMultilingualNeural", "female", "Conversation", "en-US"),
    ("en-US-MichelleNeural", "female", "News", "en-US"),
    ("en-US-GuyNeural", "male", "News/Novel", "en-US"),
    ("en-US-AndrewMultilingualNeural", "male", "Conversation", "en-US"),
    ("bn-BD-NabanitaNeural", "female", "General", "bn-BD"),
    ("bn-BD-PradeepNeural", "male", "General", "bn-BD"),
)

LICENSE = ("Microsoft Edge TTS service (unofficial keyless access; verify "
           "Microsoft terms before commercial use)")
SOURCE = "https://github.com/rany2/edge-tts"

DEFAULT_NARRATOR = "en-US-AriaNeural"
DEFAULT_DIALOGUE = "en-US-GuyNeural"

CATALOG_VOICES: list[dict] = []
for _vid, _gender, _style, _lang in _VOICES:
    CATALOG_VOICES.append({
        "voice_id": _vid,
        "name": f"{_vid} ({_style})",
        "gender": _gender,
        "accent": _lang,
        "language": _lang,
        "style": _style,
        "license": LICENSE,
        "commercial_use": False,  # verify Microsoft terms first
        "model_size_mb": 0.0,
        "engine": "edge",
        "sample_rate": 24000,
    })


def get_voice(voice_id: str) -> VoiceInfo | None:
    for entry in CATALOG_VOICES:
        if entry["voice_id"] == voice_id:
            return VoiceInfo(**entry)
    return None


def voice_names() -> list[str]:
    return [entry["voice_id"] for entry in CATALOG_VOICES]
