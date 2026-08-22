"""End-to-end pipeline test using synthetic provider (no network/model)."""
from __future__ import annotations

import wave
from pathlib import Path
from typing import Callable

import numpy as np
import soundfile as sf

import tts.manager as tts_manager
from app.core.generator import CancelledError, GenerationOptions, GenerationPipeline
from script.chunker import Chunk
from tts.base import ProviderCapabilities, SynthesisResult, TTSProvider, VoiceInfo


RATE = 22050


class FakeTTSProvider(TTSProvider):
    """Deterministic offline provider used ONLY in tests."""

    name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    def load_model(self) -> None: ...
    def unload_model(self) -> None: ...
    def is_loaded(self) -> bool:
        return True

    def list_voices(self) -> list[VoiceInfo]:
        return []

    def get_voice_info(self, voice_id: str) -> VoiceInfo | None:
        return None

    def synthesize(self, text: str, out_path: Path, voice_id: str,
                   length_scale: float = 1.0,
                   speaker_id: int | None = None) -> SynthesisResult:
        self.calls += 1
        words = max(1, len(text.split()))
        # Simulate speech at ~ natural_rate/length_scale words per minute.
        natural_wpm = 150.0
        wpm = natural_wpm / length_scale
        duration = words / wpm * 60.0
        samples = int(duration * RATE)
        t = np.linspace(0, duration, samples, endpoint=False)
        audio = (0.3 * np.sin(2 * np.pi * 300 * t)).astype(np.float32)
        sf.write(str(out_path), audio, RATE)
        return SynthesisResult(
            audio_path=out_path,
            duration_seconds=duration,
            sample_rate=RATE,
            word_count=words,
            actual_wpm=round(words / duration * 60.0, 2),
            length_scale_used=length_scale,
        )

    def synthesize_chunk(self, text: str, out_path: Path, voice_id: str,
                         length_scale: float = 1.0) -> SynthesisResult:
        return self.synthesize(text, out_path, voice_id, length_scale)

    def estimate_duration(self, text: str, voice_id: str, wpm: int) -> float:
        return len(text.split()) / wpm * 60.0

    def natural_wpm(self, voice_id: str) -> float:
        return 150.0

    def supports_emotion(self) -> bool:
        return False

    def supports_voice_cloning(self) -> bool:
        return False

    def get_license(self) -> dict:
        return {"license": "test", "commercial_use": True}

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()


def _install_fake(monkeypatch) -> FakeTTSProvider:
    """Patch the provider factory inside the pipeline module namespace."""
    fake = FakeTTSProvider()
    import app.core.generator as generator_module

    monkeypatch.setattr(generator_module, "get_provider",
                        lambda engine: fake)
    return fake


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as wf:
        return wf.getnframes() / wf.getframerate()


SCRIPT = (
    "[SCENE: Night]\n\n"
    "The old house stood silent. Nobody had entered for twenty years.\n\n"
    "But everything changed when the lights came on! What waited inside "
    "$1,000 worth of secrets? She whispered a quiet prayer."
)


def test_full_generation_pipeline(tmp_path: Path, monkeypatch):
    fake = _install_fake(monkeypatch)
    options = GenerationOptions(
        voice_id="test-voice",
        target_wpm=150,
        preset_key="HORROR",
        auto_emotion=True,
        export_format="wav",
    )
    pipeline = GenerationPipeline("Test Story", tmp_path, options)
    outcome = pipeline.run(SCRIPT)

    assert outcome.chunk_count_total >= 1
    assert outcome.chunk_count_done == outcome.chunk_count_total
    assert outcome.duration_seconds > 0
    assert outcome.output_paths and outcome.output_paths[0].exists()
    # Every chunk synthesized at least once; the WPM consistency pass may
    # legitimately re-synthesize drifting chunks (at most one retry each).
    assert fake.calls >= outcome.chunk_count_done
    assert fake.calls <= outcome.chunk_count_done * 2
    rendered = outcome.output_paths[0]
    assert _wav_duration(rendered) > outcome.duration_seconds * 0.8


def test_cache_prevents_regeneration(tmp_path: Path, monkeypatch):
    fake = _install_fake(monkeypatch)
    options = GenerationOptions(voice_id="v", target_wpm=155,
                                auto_emotion=False,
                                emotion_intensity=0.5,
                                preset_key="DOCUMENTARY")
    pipeline = GenerationPipeline("CacheTest", tmp_path, options)
    pipeline.run("One sentence here. Another sentence follows.")
    first_calls = fake.calls

    pipeline_two = GenerationPipeline("CacheTest", tmp_path, options)
    pipeline_two.run("One sentence here. Another sentence follows.")
    assert fake.calls == first_calls  # all served from cache


def test_cancel_stops_pipeline(tmp_path: Path, monkeypatch):
    _install_fake(monkeypatch)

    class CancelSoon:
        def __call__(self, state):
            if state.phase == "voice":
                raise KeyboardInterrupt

    options = GenerationOptions(voice_id="v")
    pipeline = GenerationPipeline("CancelTest", tmp_path, options,
                                  progress_callback=None)
    original_check = pipeline._check_control

    calls = {"n": 0}

    def cancel_after_first():
        calls["n"] += 1
        if calls["n"] > 0:
            pipeline.cancel()
            raise CancelledError()

    monkeypatch.setattr(pipeline, "_check_control", cancel_after_first)
    try:
        pipeline.run(SCRIPT)
        raised = False
    except CancelledError:
        raised = True
    assert raised


def test_progress_reporting(tmp_path: Path, monkeypatch):
    _install_fake(monkeypatch)
    states = []

    def callback(state):
        states.append(state.phase)

    options = GenerationOptions(voice_id="v", export_format="wav")
    pipeline = GenerationPipeline("Progress", tmp_path, options,
                                  progress_callback=callback)
    pipeline.run(SCRIPT)
    assert states[0] == "plan"
    assert "voice" in states
    assert states[-1] == "done"


def test_resume_skips_cached_chunks(tmp_path: Path, monkeypatch):
    fake = _install_fake(monkeypatch)
    from project.cache import ChunkCache

    options = GenerationOptions(voice_id="v", auto_emotion=False,
                                emotion_intensity=0.4,
                                preset_key="MYSTERY")
    pipeline = GenerationPipeline("ResumeTest", tmp_path, options)
    chunks = pipeline.build_plan(SCRIPT)
    cache = ChunkCache(tmp_path / "cache")

    # Pre-populate cache for the first chunk only.
    from emotion.prosody import plan_prosody, wpm_to_length_scale
    from project.cache import chunk_cache_key

    first = chunks[0]
    plan = plan_prosody(first.emotion or "NEUTRAL", first.effects, 0.0,
                        first.pause_after, global_intensity=0.7)
    key = chunk_cache_key(first.text, options.voice_id, options.engine,
                          round(wpm_to_length_scale(150.0, first.wpm_target)
                                * plan.length_scale, 5),
                          first.wpm_target, first.emotion)
    source = tmp_path / "seed.wav"
    t = np.linspace(0, 1.0, RATE, endpoint=False)
    sf.write(str(source), (0.2 * np.sin(2 * np.pi * 250 * t)).astype(np.float32), RATE)
    cache.put(key, source)

    outcome = pipeline.run(SCRIPT, existing_chunks=chunks)
    # First chunk served from cache; remaining chunks synthesized.
    assert outcome.cache_hits == 0  # resume path counts via status=done
    assert fake.calls == outcome.chunk_count_total - 1
