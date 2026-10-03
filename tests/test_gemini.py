"""Tests for the Gemini TTS stack (catalog, style, client, provider).

Network is fully mocked - no API key or connection needed.
"""
from __future__ import annotations

import base64
import io
import json
import urllib.error

import numpy as np
import pytest


def _pcm_bytes(seconds: float = 1.0, rate: int = 24000) -> bytes:
    t = np.linspace(0, seconds, int(seconds * rate), endpoint=False)
    pcm = (0.3 * np.sin(2 * np.pi * 220 * t) * 32767).astype("<i2")
    return pcm.tobytes()


def _api_response(pcm: bytes, rate: int = 24000) -> dict:
    return {
        "candidates": [{
            "content": {"parts": [{
                "inlineData": {
                    "mimeType": f"audio/L16;rate={rate}",
                    "data": base64.b64encode(pcm).decode("ascii"),
                }
            }]}
        }]
    }


class _FakeHTTPResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args) -> bool:
        return False


def test_catalog_has_thirty_voices():
    from tts.voices.gemini_catalog import CATALOG_VOICES, get_voice

    assert len(CATALOG_VOICES) == 30
    genders = {e["gender"] for e in CATALOG_VOICES}
    assert genders == {"female", "male"}
    assert get_voice("Charon") is not None
    assert get_voice("Nope") is None
    assert get_voice("Kore").gender == "female"


def test_style_prompts():
    from emotion.gemini_style import (
        is_dialogue_chunk,
        prompt_for_chunk,
        style_for_chunk,
    )

    neutral = style_for_chunk("NEUTRAL")
    assert "storytelling" in neutral
    fear = style_for_chunk("FEAR", intensity=1.0)
    assert "fearful" in fear
    prompt = prompt_for_chunk("Hello world.", "HAPPY")
    assert prompt.endswith("Hello world.")
    assert "cheerful" in prompt
    assert is_dialogue_chunk('"Why now?" John asked quietly.')
    assert not is_dialogue_chunk("The old house stood silent.")
    assert is_dialogue_chunk("রহিম বলল, তুমি এসো।")


def test_client_synthesizes_pcm(monkeypatch):
    from tts.providers.gemini_provider import GeminiTTSClient

    pcm = _pcm_bytes()
    captured: dict = {}

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["key"] = request.get_header("X-goog-api-key")
        body = json.loads(request.data.decode("utf-8"))
        captured["voice"] = (body["generationConfig"]["speechConfig"]
                             ["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"])
        return _FakeHTTPResponse(_api_response(pcm))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = GeminiTTSClient("test-key", "gemini-2.5-pro-preview-tts")
    out, rate = client.synthesize_pcm("Say cheerfully: Hi.", "Kore")
    assert out == pcm and rate == 24000
    assert "generateContent" in captured["url"]
    assert captured["key"] == "test-key"
    assert captured["voice"] == "Kore"


def test_client_retries_then_succeeds(monkeypatch):
    from tts.providers.gemini_provider import GeminiTTSClient

    calls = {"n": 0}

    def fake_urlopen(request, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise urllib.error.HTTPError(
                request.full_url, 503, "overloaded", {}, io.BytesIO(b"{}"))
        return _FakeHTTPResponse(_api_response(_pcm_bytes(0.5)))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda s: None)
    client = GeminiTTSClient("k", "gemini-2.5-flash-preview-tts")
    out, _ = client.synthesize_pcm("Hi.", "Puck")
    assert len(out) > 0 and calls["n"] == 3


def test_client_auth_error_is_friendly(monkeypatch):
    from app.utils.errors import UserFacingError
    from tts.providers.gemini_provider import GeminiTTSClient

    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url, 400, "bad key", {}, io.BytesIO(b"API key invalid"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    client = GeminiTTSClient("bad", "gemini-2.5-pro-preview-tts")
    with pytest.raises(UserFacingError) as exc:
        client.synthesize_pcm("Hi.", "Kore")
    assert "API key" in " ".join(exc.value.actions)


def test_client_requires_key():
    from app.utils.errors import UserFacingError
    from tts.providers.gemini_provider import GeminiTTSClient

    with pytest.raises(UserFacingError):
        GeminiTTSClient("", "gemini-2.5-pro-preview-tts")


def test_provider_writes_wav_and_tracks_usage(monkeypatch, tmp_path):
    from tts.providers.gemini_provider import GeminiTTSProvider

    pcm = _pcm_bytes(2.0)

    def fake_pcm(self, text, voice):
        assert voice == "Charon"
        return pcm, 24000

    provider = GeminiTTSProvider("k", "gemini-2.5-pro-preview-tts")
    monkeypatch.setattr(
        "tts.providers.gemini_provider.GeminiTTSClient.synthesize_pcm",
        fake_pcm)
    out = tmp_path / "chunk.wav"
    result = provider.synthesize_with_style(
        "A short test.", out, "Charon", "SAD", "DOCUMENTARY", 0.8)
    assert out.exists()
    assert result.sample_rate == 24000
    assert result.duration_seconds == pytest.approx(2.0, abs=0.05)
    assert provider.chars_synthesized == len("A short test.")
    assert provider.audio_seconds == pytest.approx(2.0, abs=0.05)


def test_provider_rejects_unknown_voice(tmp_path):
    from app.utils.errors import UserFacingError
    from tts.providers.gemini_provider import GeminiTTSProvider

    provider = GeminiTTSProvider("k")
    with pytest.raises(UserFacingError):
        provider.synthesize("Hi.", tmp_path / "x.wav", "Nope")


def test_manager_routes_gemini():
    from tts.manager import available_engines, get_provider
    from tts.providers.gemini_provider import GeminiTTSProvider

    assert available_engines() == ["edge", "gemini"]
    assert isinstance(get_provider("gemini"), GeminiTTSProvider)
    with pytest.raises(ValueError):
        get_provider("piper")


def test_chunk_key_covers_style_and_model():
    from app.core.generator import GenerationOptions, chunk_key_for
    from script.chunker import Chunk

    options = GenerationOptions()
    chunk = Chunk(chunk_id=0, scene_id=1, scene_title="S", index_in_scene=0,
                  text="The house stood silent.", emotion="FEAR")
    key_fear = chunk_key_for(chunk, options)
    calm = Chunk(chunk_id=0, scene_id=1, scene_title="S", index_in_scene=0,
                 text="The house stood silent.", emotion="CALM")
    assert chunk_key_for(calm, options) != key_fear
    assert chunk_key_for(chunk, options) == key_fear  # deterministic


def test_dialogue_chunks_route_to_dialogue_voice():
    from app.core.generator import GenerationOptions, chunk_key_for
    from script.chunker import Chunk

    options = GenerationOptions(voice_id="Charon", dialogue_voice="Puck")
    narration = Chunk(chunk_id=0, scene_id=1, scene_title="S",
                      index_in_scene=0,
                      text="The old house stood at the end of the lane.")
    dialogue = Chunk(chunk_id=1, scene_id=1, scene_title="S",
                     index_in_scene=1,
                     text='"Why now?" John asked quietly. "Because I said so."')
    assert chunk_key_for(narration, options) != chunk_key_for(dialogue, options)


def test_429_body_is_parsed_to_short_reason(monkeypatch):
    from app.utils.errors import UserFacingError
    from tts.providers.gemini_provider import GeminiTTSClient

    body = json.dumps({"error": {
        "code": 429,
        "message": "You exceeded your current quota.",
        "status": "RESOURCE_EXHAUSTED",
    }})

    def fake_urlopen(request, timeout=None):
        raise urllib.error.HTTPError(
            request.full_url, 429, "too many", {}, io.BytesIO(body.encode()))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    monkeypatch.setattr("time.sleep", lambda s: None)
    client = GeminiTTSClient("k", "gemini-2.5-pro-preview-tts")
    with pytest.raises(UserFacingError) as exc:
        client.synthesize_pcm("Hi.", "Kore")
    assert exc.value.why == "You exceeded your current quota."
    assert any("pacing" in a for a in exc.value.actions)


def test_api_pacing_between_chunks(monkeypatch, tmp_path):
    from app.core.generator import GenerationOptions, GenerationPipeline

    sleeps: list[float] = []
    monkeypatch.setattr("time.sleep", lambda s: sleeps.append(s))

    options = GenerationOptions(voice_id="Charon", auto_emotion=False,
                                api_pacing_seconds=4.0)
    pipeline = GenerationPipeline("PaceTest", tmp_path, options)
    pipeline._pace_api_calls(1, 3)  # between chunks: sleeps ~4s total
    assert sleeps and abs(sum(sleeps) - 4.0) < 0.01
    sleeps.clear()
    pipeline._pace_api_calls(3, 3)  # after final chunk: no sleep
    assert sleeps == []
    options.api_pacing_seconds = 0.0
    pipeline._pace_api_calls(1, 3)  # pacing disabled: no sleep
    assert sleeps == []


def test_pacing_sleep_is_cancellable(monkeypatch, tmp_path):
    from app.core.generator import (
        CancelledError,
        GenerationOptions,
        GenerationPipeline,
    )

    monkeypatch.setattr("time.sleep", lambda s: None)
    options = GenerationOptions(api_pacing_seconds=30.0)
    pipeline = GenerationPipeline("CancelPace", tmp_path, options)
    pipeline.cancel()
    with pytest.raises(CancelledError):
        pipeline._pace_api_calls(1, 5)
