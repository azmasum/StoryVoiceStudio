"""TTS provider abstraction.

Never hard-code the application around a single TTS model - every engine
plugs in through :class:`TTSProvider`.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VoiceInfo:
    voice_id: str
    name: str
    gender: str            # male | female
    accent: str            # e.g. en-US
    style: str             # deep | warm | cinematic | calm ...
    license: str
    commercial_use: bool
    model_size_mb: float
    sample_rate: int = 22050

    def to_dict(self) -> dict:
        return {
            "voice_id": self.voice_id,
            "name": self.name,
            "gender": self.gender,
            "accent": self.accent,
            "style": self.style,
            "license": self.license,
            "commercial_use": self.commercial_use,
            "model_size_mb": self.model_size_mb,
            "sample_rate": self.sample_rate,
        }


@dataclass(frozen=True)
class ProviderCapabilities:
    supports_emotion_natively: bool = False
    supports_voice_cloning: bool = False
    supports_pitch_control: bool = False
    multi_speaker: bool = False


@dataclass
class SynthesisResult:
    audio_path: Path
    duration_seconds: float
    sample_rate: int
    word_count: int
    actual_wpm: float
    length_scale_used: float


class TTSProvider(ABC):
    """Contract implemented by every synthesis engine."""

    name: str = "base"

    @abstractmethod
    def load_model(self) -> None: ...

    @abstractmethod
    def unload_model(self) -> None: ...

    @abstractmethod
    def is_loaded(self) -> bool: ...

    @abstractmethod
    def list_voices(self) -> list[VoiceInfo]: ...

    @abstractmethod
    def get_voice_info(self, voice_id: str) -> VoiceInfo | None: ...

    @abstractmethod
    def synthesize(
        self,
        text: str,
        out_path: Path,
        voice_id: str,
        length_scale: float = 1.0,
        speaker_id: int | None = None,
    ) -> SynthesisResult:
        """Synthesize *text* to *out_path* (16-bit PCM WAV)."""

    @abstractmethod
    def synthesize_chunk(
        self,
        text: str,
        out_path: Path,
        voice_id: str,
        length_scale: float = 1.0,
    ) -> SynthesisResult:
        """Convenience wrapper used by the generation pipeline."""

    @abstractmethod
    def estimate_duration(self, text: str, voice_id: str, wpm: int) -> float:
        """Estimated seconds for *text* at *wpm* words per minute."""

    @abstractmethod
    def natural_wpm(self, voice_id: str) -> float:
        """Measured natural speaking rate at length_scale=1.0."""

    @abstractmethod
    def supports_emotion(self) -> bool: ...

    @abstractmethod
    def supports_voice_cloning(self) -> bool: ...

    @abstractmethod
    def get_license(self) -> dict: ...

    @abstractmethod
    def get_capabilities(self) -> ProviderCapabilities: ...
