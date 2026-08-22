"""Piper TTS provider - real, local, offline neural speech synthesis.

Piper (https://github.com/rhasspy/piper) runs ONNX models on CPU; no GPU,
API key or internet connection is required after the voice model is
downloaded. Voice models from rhasspy/piper-voices are MIT licensed.
"""
from __future__ import annotations

import logging
import time
import wave
from pathlib import Path

from app.utils.errors import UserFacingError
from models.downloader import installed_manifest, voice_model_paths
from tts.base import (
    ProviderCapabilities,
    SynthesisResult,
    TTSProvider,
    VoiceInfo,
)

log = logging.getLogger("tts")


def _import_piper():
    try:
        import piper  # noqa: F401
        return piper
    except ImportError as exc:
        raise UserFacingError(
            what="The Piper TTS engine is not installed.",
            why="The 'piper-tts' Python package is missing from this environment.",
            actions=[
                "Run: pip install piper-tts",
                "Or launch via run_dev.bat which installs all dependencies.",
            ],
        ) from exc


class PiperProvider(TTSProvider):
    name = "piper"

    def __init__(self) -> None:
        self._voice: object | None = None
        self._loaded_voice_id: str = ""
        self._wpm_cache: dict[str, float] = {}

    # -- model lifecycle -----------------------------------------------------

    def load_model(self) -> None:
        """No global model for Piper - voices load lazily per voice_id."""

    def unload_model(self) -> None:
        self._voice = None
        self._loaded_voice_id = ""

    def is_loaded(self) -> bool:
        return self._voice is not None

    def _load_voice(self, voice_id: str):
        if self._loaded_voice_id == voice_id and self._voice is not None:
            return self._voice
        model_path, config_path = voice_model_paths(voice_id)
        if not model_path.exists() or not config_path.exists():
            raise UserFacingError(
                what=f"Voice '{voice_id}' is not downloaded.",
                why=f"Expected model files under {model_path.parent}.",
                actions=[
                    "Open Models > Model Manager and download this voice.",
                    "Or use CLI: storyvoice download-model " + voice_id,
                ],
            )
        piper = _import_piper()
        t0 = time.time()
        try:
            voice = piper.PiperVoice.load(str(model_path), str(config_path))
        except TypeError:
            # Older piper versions take only the model path.
            voice = piper.PiperVoice.load(str(model_path))
        self._voice = voice
        self._loaded_voice_id = voice_id
        log.info("Loaded Piper voice %s in %.2fs", voice_id, time.time() - t0)
        return voice

    # -- synthesis ------------------------------------------------------------

    def synthesize(
        self,
        text: str,
        out_path: Path,
        voice_id: str,
        length_scale: float = 1.0,
        speaker_id: int | None = None,
    ) -> SynthesisResult:
        text = " ".join(text.split())
        if not text:
            raise ValueError("Cannot synthesize empty text.")
        voice = self._load_voice(voice_id)
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        started = time.time()
        with wave.open(str(out_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self._sample_rate(voice))
            self._synthesize_wav(voice, text, wav_file, length_scale, speaker_id)

        duration = _wave_duration(out_path)
        words = len(text.split())
        actual_wpm = (words / duration * 60.0) if duration > 0 else 0.0
        result = SynthesisResult(
            audio_path=out_path,
            duration_seconds=duration,
            sample_rate=self._sample_rate(voice),
            word_count=words,
            actual_wpm=round(actual_wpm, 2),
            length_scale_used=length_scale,
        )
        log.debug("Synth %d words in %.2fs (%.1f WPM)", words, time.time() - started,
                  result.actual_wpm)
        return result

    @staticmethod
    def _sample_rate(voice: object) -> int:
        config = getattr(voice, "config", None)
        rate = getattr(config, "sample_rate", 22050)
        return int(rate)

    @staticmethod
    def _synthesize_wav(voice, text: str, wav_file, length_scale: float,
                        speaker_id: int | None) -> None:
        """Handle both new-style (>=1.3) and legacy piper APIs."""
        synth_config = None
        try:
            from piper import SynthesisConfig  # type: ignore[attr-defined]

            kwargs: dict = {"lengthScale": length_scale}
            if speaker_id is not None:
                kwargs["speakerId"] = speaker_id
            try:
                synth_config = SynthesisConfig(**kwargs)
            except TypeError:
                kwargs = {"length_scale": length_scale}
                if speaker_id is not None:
                    kwargs["speaker_id"] = speaker_id
                synth_config = SynthesisConfig(**kwargs)
        except ImportError:
            synth_config = None

        if synth_config is not None:
            try:
                voice.synthesize_wav(text, wav_file, syn_config=synth_config)
                return
            except TypeError:
                pass  # fall through to legacy call signature
        try:
            voice.synthesize_wav(
                text, wav_file, speaker_id=speaker_id, length_scale=length_scale
            )
        except TypeError:
            voice.synthesize_wav(text, wav_file)

    def synthesize_chunk(
        self,
        text: str,
        out_path: Path,
        voice_id: str,
        length_scale: float = 1.0,
    ) -> SynthesisResult:
        return self.synthesize(text, out_path, voice_id, length_scale)

    # -- metadata / measurement ----------------------------------------------

    def natural_wpm(self, voice_id: str) -> float:
        """Measure the voice's natural rate once and cache it."""
        if voice_id in self._wpm_cache:
            return self._wpm_cache[voice_id]
        calibration_text = (
            "The old house stood at the end of the lane, its windows dark "
            "against the evening sky. Nobody had lived there for twenty "
            "years, and nobody wanted to talk about the reason why."
        )
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calibration.wav"
            result = self.synthesize(calibration_text, path, voice_id,
                                     length_scale=1.0)
        wpm = max(60.0, min(300.0, result.actual_wpm))
        self._wpm_cache[voice_id] = wpm
        log.info("Voice %s natural rate measured: %.1f WPM", voice_id, wpm)
        return wpm

    def estimate_duration(self, text: str, voice_id: str, wpm: int) -> float:
        words = max(1, len(text.split()))
        return round(words / wpm * 60.0, 3)

    def list_voices(self) -> list[VoiceInfo]:
        manifest = installed_manifest()
        from tts.voices.catalog import CATALOG_VOICES

        infos = []
        for entry in CATALOG_VOICES:
            installed = entry["voice_id"] in manifest
            info = VoiceInfo(**{k: entry[k] for k in VoiceInfo.__dataclass_fields__})
            _ = installed
            infos.append(info)
        return infos

    def get_voice_info(self, voice_id: str) -> VoiceInfo | None:
        for voice in self.list_voices():
            if voice.voice_id == voice_id:
                return voice
        return None

    def supports_emotion(self) -> bool:
        return False  # emotion handled by prosody planning + pauses, not natively

    def supports_voice_cloning(self) -> bool:
        return False

    def get_license(self) -> dict:
        return {
            "engine": "piper-tts",
            "license": "MIT",
            "source": "https://github.com/rhasspy/piper",
            "commercial_use": True,
        }

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_emotion_natively=False,
            supports_voice_cloning=False,
            supports_pitch_control=False,
            multi_speaker=False,
        )


def _wave_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate) if rate else 0.0
