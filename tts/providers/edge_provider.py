"""EdgeTTS provider - free keyless neural narration via Microsoft Edge.

Uses the `edge-tts` package (WebSocket SSML, mp3 24kHz out) with emotion
mapped onto real prosody knobs: rate% and pitchHz per chunk. MP3 bytes are
decoded to WAV with the imageio-ffmpeg binary (no system FFmpeg needed).

Free, no API key, no billing - but unofficial access: be polite (the
pipeline paces requests) and verify Microsoft's terms before any
commercial use.
"""
from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from app.utils.errors import UserFacingError
from tts.base import (
    ProviderCapabilities,
    SynthesisResult,
    TTSProvider,
    VoiceInfo,
)

log = logging.getLogger("tts")

OUTPUT_SAMPLE_RATE = 44100


def _require_edge_tts():
    try:
        import edge_tts

        return edge_tts
    except ImportError as exc:
        raise UserFacingError(
            what="The EdgeTTS package is not installed.",
            why="The 'edge-tts' Python package is missing.",
            actions=[
                "Run: pip install edge-tts imageio-ffmpeg",
                "Or launch via run_dev.bat which installs requirements.",
            ],
        ) from exc


def _decode_mp3(mp3_path: Path, wav_path: Path) -> None:
    from export.ffmpeg import ffmpeg_available, mp3_to_wav

    if not ffmpeg_available():
        raise UserFacingError(
            what="No audio decoder available.",
            why="MP3 decoding needs FFmpeg (imageio-ffmpeg package).",
            actions=[
                "Run: pip install imageio-ffmpeg",
                "Or set STORYVOICE_FFMPEG to an ffmpeg.exe path.",
            ],
        )
    mp3_to_wav(mp3_path, wav_path, OUTPUT_SAMPLE_RATE)


class EdgeTTSProvider(TTSProvider):
    name = "edge"

    def __init__(self) -> None:
        self._wpm_cache: dict[str, float] = {}
        self.chars_synthesized = 0
        self.audio_seconds = 0.0

    # -- model lifecycle (cloud: nothing to load) ---------------------------

    def load_model(self) -> None:
        pass

    def unload_model(self) -> None:
        pass

    def is_loaded(self) -> bool:
        return True

    # -- synthesis -----------------------------------------------------------

    @staticmethod
    def _prosody(emotion: str, intensity: float,
                 length_scale: float = 1.0) -> tuple[str, str]:
        """Map emotion+pace onto edge-tts (rate%, pitchHz) strings."""
        from emotion.prosody import EMOTION_PROFILES

        profile = EMOTION_PROFILES.get((emotion or "NEUTRAL").upper(),
                                       EMOTION_PROFILES["NEUTRAL"])
        strength = max(0.0, min(1.0, intensity))
        scale = profile.rate_scale
        blended = 1.0 + (scale - 1.0) * strength
        total = blended * max(0.5, min(1.5, length_scale))
        rate_pct = (1.0 / total - 1.0) * 100.0
        rate_pct = max(-30.0, min(30.0, rate_pct))
        semitones = profile.pitch_shift_semitones * strength
        pitch_hz = max(-40.0, min(40.0, semitones * 8.0))
        rate = f"{rate_pct:+.0f}%"
        pitch = f"{pitch_hz:+.0f}Hz"
        return rate, pitch

    def _stream_mp3(self, text: str, voice_id: str, rate: str,
                    pitch: str) -> bytes:
        edge_tts = _require_edge_tts()

        async def _run() -> bytes:
            communicate = edge_tts.Communicate(
                text, voice_id, rate=rate, pitch=pitch)
            data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    data += chunk["data"]
            return data

        try:
            return asyncio.run(_run())
        except Exception as exc:  # noqa: BLE001
            raise UserFacingError(
                what="EdgeTTS request failed.",
                why=str(exc)[:300],
                actions=[
                    "Check your internet connection and retry.",
                    "The free endpoint throttles abuse - raise 'API pacing'.",
                ],
            ) from exc

    def synthesize_with_style(
        self,
        text: str,
        out_path: Path,
        voice_id: str,
        emotion: str = "NEUTRAL",
        preset_key: str = "DOCUMENTARY",
        intensity: float = 0.7,
        length_scale: float = 1.0,
    ) -> SynthesisResult:
        from tts.voices.edge_catalog import get_voice as _get_voice

        if _get_voice(voice_id) is None:
            raise UserFacingError(
                what=f"Unknown voice '{voice_id}'.",
                why="This voice is not in the EdgeTTS catalog.",
                actions=["Pick one of the voices in the Voice panel."],
            )
        text = " ".join(text.split())
        if not text:
            raise ValueError("Cannot synthesize empty text.")
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        rate, pitch = self._prosody(emotion, intensity, length_scale)
        started = time.time()
        mp3_data = self._stream_mp3(text, voice_id, rate, pitch)
        if not mp3_data:
            raise UserFacingError(
                what="EdgeTTS returned no audio.",
                why="Empty response stream.",
                actions=["Retry the generation."],
            )
        tmp_mp3 = out_path.with_suffix(".edge.mp3")
        tmp_mp3.write_bytes(mp3_data)
        try:
            _decode_mp3(tmp_mp3, out_path)
        finally:
            tmp_mp3.unlink(missing_ok=True)

        self.chars_synthesized += len(text)
        duration = _wav_duration(out_path)
        self.audio_seconds += duration
        words = len(text.split())
        actual_wpm = (words / duration * 60.0) if duration > 0 else 0.0
        result = SynthesisResult(
            audio_path=out_path,
            duration_seconds=duration,
            sample_rate=OUTPUT_SAMPLE_RATE,
            word_count=words,
            actual_wpm=round(actual_wpm, 2),
            length_scale_used=length_scale,
        )
        log.debug("EdgeTTS synth %d words in %.1fs (%.1f WPM)", words,
                  time.time() - started, result.actual_wpm)
        return result

    def synthesize(
        self,
        text: str,
        out_path: Path,
        voice_id: str,
        length_scale: float = 1.0,
        speaker_id: int | None = None,
    ) -> SynthesisResult:
        return self.synthesize_with_style(
            text, out_path, voice_id, "NEUTRAL", "DOCUMENTARY", 0.7,
            length_scale)

    def synthesize_chunk(
        self,
        text: str,
        out_path: Path,
        voice_id: str,
        length_scale: float = 1.0,
    ) -> SynthesisResult:
        return self.synthesize(text, out_path, voice_id, length_scale)

    # -- metadata -------------------------------------------------------------

    def natural_wpm(self, voice_id: str) -> float:
        if voice_id in self._wpm_cache:
            return self._wpm_cache[voice_id]
        from tts.voices.edge_catalog import get_voice as _get_voice

        info = _get_voice(voice_id)
        accent = (info.accent if info else "") or ""
        if accent.lower().startswith("bn"):
            calibration = ("একটি ছোট গ্রামে একজন বৃদ্ধ কৃষক বাস করতেন। "
                           "প্রতিদিন ভোরে তিনি মাঠে কাজ করতে যেতেন।")
        else:
            calibration = (
                "The old house stood at the end of the lane, its windows "
                "dark against the evening sky. Nobody had lived there for "
                "twenty years, and nobody wanted to talk about the reason why."
            )
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calibration.wav"
            result = self.synthesize(calibration, path, voice_id,
                                     length_scale=1.0)
        wpm = max(60.0, min(300.0, result.actual_wpm))
        self._wpm_cache[voice_id] = wpm
        log.info("Voice %s natural rate measured: %.1f WPM", voice_id, wpm)
        return wpm

    def estimate_duration(self, text: str, voice_id: str, wpm: int) -> float:
        words = max(1, len(text.split()))
        return round(words / max(60, wpm) * 60.0, 3)

    def list_voices(self) -> list[VoiceInfo]:
        from tts.voices.edge_catalog import CATALOG_VOICES

        return [VoiceInfo(**entry) for entry in CATALOG_VOICES]

    def get_voice_info(self, voice_id: str) -> VoiceInfo | None:
        from tts.voices.edge_catalog import get_voice as _get_voice

        return _get_voice(voice_id)

    def supports_emotion(self) -> bool:
        return True  # via rate/pitch prosody knobs

    def supports_voice_cloning(self) -> bool:
        return False

    def get_license(self) -> dict:
        return {
            "engine": "Microsoft Edge TTS (keyless)",
            "license": "Microsoft service terms - verify before commercial use",
            "source": "https://github.com/rany2/edge-tts",
            "commercial_use": False,
        }

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_emotion_natively=True,
            supports_voice_cloning=False,
            supports_pitch_control=True,
            multi_speaker=False,
        )


def _wav_duration(path: Path) -> float:
    import wave

    with wave.open(str(path), "rb") as wf:
        rate = wf.getframerate() or 1
        return wf.getnframes() / rate
