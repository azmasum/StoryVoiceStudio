"""Gemini TTS voice catalog (prebuilt studio voices, 30).

Voices work on every Gemini TTS model and with any style prompt; the
descriptor summarizes each voice's natural tone. Source: Google AI for
Developers speech-generation docs + Gemini Live voice table.
"""
from __future__ import annotations

from tts.base import VoiceInfo

GEMINI_MODELS = (
    "gemini-2.5-pro-preview-tts",
    "gemini-2.5-flash-preview-tts",
)
DEFAULT_MODEL = "gemini-2.5-pro-preview-tts"

# (voice name, gender, descriptor)
_VOICES: tuple[tuple[str, str, str], ...] = (
    ("Zephyr", "female", "Bright"),
    ("Kore", "female", "Firm"),
    ("Leda", "female", "Youthful"),
    ("Aoede", "female", "Breezy"),
    ("Callirrhoe", "female", "Easy-going"),
    ("Autonoe", "female", "Bright"),
    ("Erinome", "female", "Clear"),
    ("Despina", "female", "Smooth"),
    ("Laomedeia", "female", "Upbeat"),
    ("Achernar", "female", "Soft"),
    ("Vindemiatrix", "female", "Gentle"),
    ("Sulafat", "female", "Warm"),
    ("Gacrux", "female", "Versatile"),
    ("Pulcherrima", "female", "Versatile"),
    ("Puck", "male", "Upbeat"),
    ("Charon", "male", "Informative"),
    ("Fenrir", "male", "Excitable"),
    ("Orus", "male", "Firm"),
    ("Enceladus", "male", "Breathy"),
    ("Iapetus", "male", "Clear"),
    ("Umbriel", "male", "Easy-going"),
    ("Algieba", "male", "Smooth"),
    ("Algenib", "male", "Gravelly"),
    ("Rasalgethi", "male", "Informative"),
    ("Alnilam", "male", "Firm"),
    ("Schedar", "male", "Even"),
    ("Achird", "male", "Friendly"),
    ("Zubenelgenubi", "male", "Casual"),
    ("Sadachbia", "male", "Lively"),
    ("Sadaltager", "male", "Knowledgeable"),
)

LICENSE = "Google Gemini API Terms of Service"
SOURCE = "https://ai.google.dev/gemini-api/docs/speech-generation"

# The API detects the input language automatically (70+ languages,
# including Bengali bn-BD and English en-US/en-IN).
LANGUAGES = ("auto", "bn-BD", "en-US")

DEFAULT_NARRATOR = "Charon"   # documentary/narration pick per voice playbook
DEFAULT_DIALOGUE = "Puck"     # contrasting timbre so speakers stay distinct

CATALOG_VOICES: list[dict] = []
for _name, _gender, _desc in _VOICES:
    CATALOG_VOICES.append({
        "voice_id": _name,
        "name": f"{_name} ({_desc})",
        "gender": _gender,
        "accent": "auto",
        "language": "auto",
        "style": _desc,
        "license": LICENSE,
        "commercial_use": True,  # per Gemini API paid-tier terms; verify
        "model_size_mb": 0.0,    # cloud voice - nothing to download
        "engine": "gemini",
        "sample_rate": 24000,
    })


def get_voice(voice_id: str) -> VoiceInfo | None:
    for entry in CATALOG_VOICES:
        if entry["voice_id"] == voice_id:
            return VoiceInfo(**entry)
    return None


def voice_names() -> list[str]:
    return [entry["voice_id"] for entry in CATALOG_VOICES]


def find_by_style(style: str, gender: str | None = None) -> str | None:
    for entry in CATALOG_VOICES:
        if entry["style"].lower() == style.lower() and (
                gender is None or entry["gender"] == gender):
            return entry["voice_id"]
    return None
