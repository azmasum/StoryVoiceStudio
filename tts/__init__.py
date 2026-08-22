"""TTS provider abstraction and engines."""
from tts.base import ProviderCapabilities, SynthesisResult, TTSProvider, VoiceInfo
from tts.manager import available_engines, get_provider

__all__ = [
    "TTSProvider",
    "VoiceInfo",
    "SynthesisResult",
    "ProviderCapabilities",
    "available_engines",
    "get_provider",
]
