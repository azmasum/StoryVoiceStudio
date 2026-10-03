"""Gemini TTS provider - cloud neural narration via the Gemini API.

Uses the generateContent REST endpoint with stdlib urllib only (no heavy
SDK), so the frozen app stays lean. Audio comes back as base64 16-bit PCM
mono (24 kHz) with a SynthID watermark applied by Google.

Billing: the API is paid (see AI Studio billing); every generation tracks
characters + audio seconds so the UI can show usage. The API key lives in
local settings only and is never logged.
"""
from __future__ import annotations

import base64
import json
import logging
import time
import urllib.error
import urllib.request
from pathlib import Path

from app.utils.errors import UserFacingError
from emotion.gemini_style import prompt_for_chunk
from tts.base import (
    ProviderCapabilities,
    SynthesisResult,
    TTSProvider,
    VoiceInfo,
)
from tts.voices.gemini_catalog import (
    DEFAULT_MODEL,
    GEMINI_MODELS,
    get_voice,
)

log = logging.getLogger("tts")

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_SAMPLE_RATE = 24000
REQUEST_TIMEOUT = 180
MAX_RETRIES = 3


class GeminiAPIError(UserFacingError):
    pass


def _friendly_http_error(status: int, body: str, model: str) -> GeminiAPIError:
    snippet = body[:300].replace("\n", " ")
    if status in (400, 401, 403):
        return GeminiAPIError(
            what="Gemini API rejected the request.",
            why=f"HTTP {status}: {snippet or 'invalid key or model'}.",
            actions=[
                "Check the API key in Settings (AI Studio > Get API key).",
                f"Confirm the model name '{model}' is available to your key.",
                "Free-tier keys have strict rate limits - retry in a minute.",
            ],
        )
    if status == 404:
        return GeminiAPIError(
            what=f"Model '{model}' was not found.",
            why=f"HTTP 404: {snippet}.",
            actions=[
                "Pick another model in Settings "
                f"({', '.join(GEMINI_MODELS)}).",
                "The preview model name may have changed - see AI Studio docs.",
            ],
        )
    if status == 429:
        return GeminiAPIError(
            what="Gemini API quota exhausted.",
            why=f"HTTP 429: {snippet or 'too many requests'}.",
            actions=[
                "Wait a minute and run generation again.",
                "Enable billing in AI Studio for higher limits.",
                "Generate in smaller batches (Preview renders).",
            ],
        )
    return GeminiAPIError(
        what="Gemini TTS request failed.",
        why=f"HTTP {status}: {snippet}.",
        actions=[
            "Check your internet connection and retry.",
            "If it persists, check https://status.cloud.google.com.",
        ],
    )


class GeminiTTSClient:
    """Minimal generateContent client for the TTS models."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL,
                 timeout: int = REQUEST_TIMEOUT) -> None:
        if not api_key:
            raise GeminiAPIError(
                what="A Gemini API key is required.",
                why="No key is configured.",
                actions=[
                    "Open Settings, paste a key from "
                    "https://aistudio.google.com/apikey, and retry.",
                ],
            )
        if model not in GEMINI_MODELS:
            raise GeminiAPIError(
                what=f"Unknown Gemini TTS model '{model}'.",
                why="Only the bundled TTS models are supported.",
                actions=[f"Choose one of: {', '.join(GEMINI_MODELS)}."],
            )
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _post(self, payload: dict) -> dict:
        url = f"{API_BASE}/models/{self.model}:generateContent"
        data = json.dumps(payload).encode("utf-8")
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            request = urllib.request.Request(
                url, data=data,
                headers={
                    "Content-Type": "application/json",
                    "x-goog-api-key": self.api_key,
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request,
                                            timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                body = ""
                try:
                    body = exc.read().decode("utf-8", "replace")
                except Exception:  # noqa: BLE001
                    pass
                if exc.code in (429, 500, 502, 503) and attempt < MAX_RETRIES - 1:
                    wait = self._retry_after(exc, attempt)
                    log.warning("Gemini HTTP %s - retry in %.1fs", exc.code,
                                wait)
                    time.sleep(wait)
                    last_error = exc
                    continue
                raise _friendly_http_error(exc.code, body, self.model) from exc
            except (urllib.error.URLError, TimeoutError) as exc:
                if attempt < MAX_RETRIES - 1:
                    wait = 2.0 * (attempt + 1)
                    log.warning("Gemini network error - retry in %.1fs", wait)
                    time.sleep(wait)
                    last_error = exc
                    continue
                raise GeminiAPIError(
                    what="Could not reach the Gemini API.",
                    why=str(exc),
                    actions=["Check your internet connection and retry."],
                ) from exc
        assert last_error is not None
        raise GeminiAPIError(
            what="Gemini TTS request failed after retries.",
            why=str(last_error),
            actions=["Wait a minute and run generation again."],
        ) from last_error

    @staticmethod
    def _retry_after(exc: urllib.error.HTTPError, attempt: int) -> float:
        try:
            retry = exc.headers.get("Retry-After")
            if retry and float(retry) > 0:
                return min(float(retry), 60.0)
        except Exception:  # noqa: BLE001
            pass
        return 2.0 * (attempt + 1)

    def synthesize_pcm(self, text: str, voice: str) -> tuple[bytes, int]:
        """Return (raw s16le mono PCM, sample rate)."""
        payload = {
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": voice}
                    }
                },
            },
        }
        response = self._post(payload)
        try:
            parts = response["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError, TypeError) as exc:
            raise GeminiAPIError(
                what="Gemini returned no audio.",
                why=str(response)[:300],
                actions=[
                    "Retry the generation.",
                    "If text was blocked by safety filters, rephrase it.",
                ],
            ) from exc
        for part in parts:
            inline = part.get("inlineData", {}) if isinstance(part, dict) else {}
            data = inline.get("data", "")
            if data:
                rate = DEFAULT_SAMPLE_RATE
                mime = inline.get("mimeType", "")
                if "rate=" in mime:
                    try:
                        rate = int(mime.split("rate=")[1].split(";")[0].split(",")[0])
                    except ValueError:
                        pass
                return base64.b64decode(data), rate
        raise GeminiAPIError(
            what="Gemini returned no audio.",
            why="Response had no inlineData audio part.",
            actions=["Retry the generation."],
        )


class GeminiTTSProvider(TTSProvider):
    name = "gemini"

    def __init__(self, api_key: str = "", model: str = DEFAULT_MODEL) -> None:
        self._api_key = api_key
        self._model = model if model in GEMINI_MODELS else DEFAULT_MODEL
        self._client: GeminiTTSClient | None = None
        self._wpm_cache: dict[str, float] = {}
        self.chars_synthesized = 0
        self.audio_seconds = 0.0

    def configure(self, api_key: str, model: str) -> None:
        if api_key != self._api_key or model != self._model:
            self._api_key = api_key
            self._model = model if model in GEMINI_MODELS else DEFAULT_MODEL
            self._client = None

    @property
    def client(self) -> GeminiTTSClient:
        if self._client is None:
            self._client = GeminiTTSClient(self._api_key, self._model)
        return self._client

    # -- model lifecycle (cloud: nothing to load) ---------------------------

    def load_model(self) -> None:
        pass

    def unload_model(self) -> None:
        self._client = None

    def is_loaded(self) -> bool:
        return True

    # -- synthesis -----------------------------------------------------------

    def synthesize(
        self,
        text: str,
        out_path: Path,
        voice_id: str,
        length_scale: float = 1.0,
        speaker_id: int | None = None,
    ) -> SynthesisResult:
        return self.synthesize_with_style(
            text, out_path, voice_id, emotion="NEUTRAL")

    def synthesize_with_style(
        self,
        text: str,
        out_path: Path,
        voice_id: str,
        emotion: str = "NEUTRAL",
        preset_key: str = "DOCUMENTARY",
        intensity: float = 0.7,
    ) -> SynthesisResult:
        """Synthesize with an emotion/preset style direction."""
        from tts.voices.gemini_catalog import get_voice as _get_voice

        if _get_voice(voice_id) is None:
            raise GeminiAPIError(
                what=f"Unknown voice '{voice_id}'.",
                why="This voice is not in the Gemini catalog.",
                actions=["Pick one of the 30 voices in the Voice panel."],
            )
        text = " ".join(text.split())
        if not text:
            raise ValueError("Cannot synthesize empty text.")
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        prompt = prompt_for_chunk(text, emotion, preset_key, intensity)
        started = time.time()
        pcm, rate = self.client.synthesize_pcm(prompt, voice_id)

        import wave

        with wave.open(str(out_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(rate)
            wav_file.writeframes(pcm)

        self.chars_synthesized += len(text)
        duration = len(pcm) / 2 / rate if rate else 0.0
        self.audio_seconds += duration
        words = len(text.split())
        actual_wpm = (words / duration * 60.0) if duration > 0 else 0.0
        result = SynthesisResult(
            audio_path=out_path,
            duration_seconds=duration,
            sample_rate=rate,
            word_count=words,
            actual_wpm=round(actual_wpm, 2),
            length_scale_used=1.0,
        )
        log.debug("Gemini synth %d words in %.1fs (%.1f WPM)", words,
                  time.time() - started, result.actual_wpm)
        return result

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
        calibration = (
            "The old house stood at the end of the lane, its windows dark "
            "against the evening sky. Nobody had lived there for twenty "
            "years, and nobody wanted to talk about the reason why."
        )
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calibration.wav"
            result = self.synthesize(calibration, path, voice_id)
        wpm = max(60.0, min(300.0, result.actual_wpm))
        self._wpm_cache[voice_id] = wpm
        log.info("Voice %s natural rate measured: %.1f WPM", voice_id, wpm)
        return wpm

    def estimate_duration(self, text: str, voice_id: str, wpm: int) -> float:
        words = max(1, len(text.split()))
        return round(words / max(60, wpm) * 60.0, 3)

    def list_voices(self) -> list[VoiceInfo]:
        from tts.voices.gemini_catalog import CATALOG_VOICES

        return [VoiceInfo(**entry) for entry in CATALOG_VOICES]

    def get_voice_info(self, voice_id: str) -> VoiceInfo | None:
        return get_voice(voice_id)

    def supports_emotion(self) -> bool:
        return True  # via natural-language style directions

    def supports_voice_cloning(self) -> bool:
        return False

    def get_license(self) -> dict:
        return {
            "engine": "Google Gemini API (gemini-2.5 TTS)",
            "license": "Gemini API Terms of Service (paid API)",
            "source": "https://ai.google.dev/gemini-api/docs/speech-generation",
            "commercial_use": True,  # per paid-tier terms; verify in console
        }

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_emotion_natively=True,
            supports_voice_cloning=False,
            supports_pitch_control=False,
            multi_speaker=False,  # per-chunk voice routing instead (v1)
        )
