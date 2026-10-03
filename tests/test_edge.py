"""Tests for the EdgeTTS provider (network + ffmpeg fully mocked)."""
from __future__ import annotations

import sys
import types

import numpy as np
import pytest


def _install_fake_edge_tts(monkeypatch, captured):
    """Fake edge_tts module: records kwargs, streams canned mp3 bytes."""
    fake = types.ModuleType("edge_tts")

    class FakeCommunicate:
        def __init__(self, text, voice, rate="+0%", pitch="+0Hz"):
            captured["text"] = text
            captured["voice"] = voice
            captured["rate"] = rate
            captured["pitch"] = pitch

        async def stream(self):
            yield {"type": "audio", "data": b"FAKEMP3" * 100}
            yield {"type": "words", "data": {}}

    fake.Communicate = FakeCommunicate
    monkeypatch.setitem(sys.modules, "edge_tts", fake)


def _fake_mp3_to_wav(monkeypatch, seconds=2.0, rate=44100):
    import export.ffmpeg as ffmpeg_mod

    def fake(src, dest, sample_rate=44100):
        import soundfile as sf

        n = int(seconds * sample_rate)
        t = np.linspace(0, seconds, n, endpoint=False)
        sf.write(str(dest),
                 (0.3 * np.sin(2 * np.pi * 220 * t)).astype(np.float32),
                 sample_rate)

    monkeypatch.setattr(ffmpeg_mod, "mp3_to_wav", fake)


def test_edge_catalog():
    from tts.voices import edge_catalog
    from tts.voices.catalog import get_engine, voices_for_engine

    assert len(edge_catalog.CATALOG_VOICES) == 8
    assert len(voices_for_engine("edge")) == 8
    assert len(voices_for_engine("gemini")) == 30
    assert get_engine("bn-BD-NabanitaNeural") == "edge"
    assert get_engine("Charon") == "gemini"
    voice = edge_catalog.get_voice("bn-BD-PradeepNeural")
    assert voice is not None and voice.gender == "male"


def test_prosody_mapping():
    from tts.providers.edge_provider import EdgeTTSProvider

    rate, pitch = EdgeTTSProvider._prosody("NEUTRAL", 0.7)
    assert rate == "+0%" and pitch == "+0Hz"
    rate, _ = EdgeTTSProvider._prosody("FEAR", 1.0)
    assert rate.startswith("-")  # slower
    rate, _ = EdgeTTSProvider._prosody("EXCITED", 1.0)
    assert rate.startswith("+")  # faster
    rate, _ = EdgeTTSProvider._prosody("SAD", 1.0, length_scale=2.0)
    assert rate == "-30%"  # clamped


def test_synthesize_writes_wav(monkeypatch, tmp_path):
    from tts.providers.edge_provider import EdgeTTSProvider

    captured: dict = {}
    _install_fake_edge_tts(monkeypatch, captured)
    _fake_mp3_to_wav(monkeypatch, seconds=3.0)
    provider = EdgeTTSProvider()
    out = tmp_path / "chunk.wav"
    result = provider.synthesize_with_style(
        "Hello world test.", out, "en-US-AriaNeural", "HAPPY",
        "DOCUMENTARY", 0.8)
    assert out.exists()
    assert captured["voice"] == "en-US-AriaNeural"
    assert result.sample_rate == 44100
    assert result.duration_seconds == pytest.approx(3.0, abs=0.05)
    assert provider.chars_synthesized == len("Hello world test.")
    assert provider.audio_seconds == pytest.approx(3.0, abs=0.05)


def test_unknown_voice_rejected(tmp_path):
    from app.utils.errors import UserFacingError
    from tts.providers.edge_provider import EdgeTTSProvider

    with pytest.raises(UserFacingError):
        EdgeTTSProvider().synthesize("Hi.", tmp_path / "x.wav", "Nope")


def test_natural_wpm_caches(monkeypatch, tmp_path):
    from tts.providers.edge_provider import EdgeTTSProvider

    captured: dict = {}
    _install_fake_edge_tts(monkeypatch, captured)
    _fake_mp3_to_wav(monkeypatch, seconds=4.0)
    provider = EdgeTTSProvider()
    first = provider.natural_wpm("en-US-AriaNeural")
    second = provider.natural_wpm("en-US-AriaNeural")
    assert first == second
    assert 60.0 <= first <= 300.0


def test_manager_routes_both_engines():
    from tts.manager import available_engines, get_provider
    from tts.providers.edge_provider import EdgeTTSProvider
    from tts.providers.gemini_provider import GeminiTTSProvider

    assert available_engines() == ["edge", "gemini"]
    assert isinstance(get_provider("edge"), EdgeTTSProvider)
    assert isinstance(get_provider("gemini"), GeminiTTSProvider)


def test_edge_retry_corrects_drift(monkeypatch, tmp_path):
    """A drifting edge chunk is re-synthesized once with corrected rate."""
    from app.core.generator import GenerationOptions, GenerationPipeline
    from script.chunker import Chunk
    from tts.base import SynthesisResult

    import soundfile as sf

    calls = {"n": 0, "scales": []}

    class _FakeEdge:
        def natural_wpm(self, voice_id):
            return 150.0

        def synthesize_with_style(self, text, out_path, voice_id,
                                  emotion="NEUTRAL", preset_key="DOCUMENTARY",
                                  intensity=0.7, length_scale=1.0):
            calls["n"] += 1
            calls["scales"].append(length_scale)
            # First attempt drifts badly, retry lands on target.
            wpm = 100.0 if calls["n"] == 1 else 155.0
            words = len(text.split())
            dur = words / wpm * 60.0
            sr = 44100
            t = np.linspace(0, dur, int(dur * sr), endpoint=False)
            sf.write(str(out_path),
                     (0.2 * np.sin(2 * np.pi * 200 * t)).astype(np.float32),
                     sr)
            return SynthesisResult(audio_path=out_path, duration_seconds=dur,
                                   sample_rate=sr, word_count=words,
                                   actual_wpm=wpm, length_scale_used=length_scale)

        def synthesize(self, text, out_path, voice_id, length_scale=1.0):
            return self.synthesize_with_style(
                text, out_path, voice_id, length_scale=length_scale)

    options = GenerationOptions(voice_id="en-US-AriaNeural", engine="edge",
                                auto_emotion=False)
    pipeline = GenerationPipeline("RetryTest", tmp_path, options)
    chunk = Chunk(chunk_id=0, scene_id=1, scene_title="S", index_in_scene=0,
                  text="The quick brown fox jumps over the lazy dog",
                  wpm_target=155)
    pipeline._synthesize_chunk(_FakeEdge(), chunk)
    assert calls["n"] == 2  # initial + one correction
    assert calls["scales"][1] != calls["scales"][0]
