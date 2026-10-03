"""Voice-quality regression tests: pacing clamps, Bengali chunking, clicks."""
from __future__ import annotations

import numpy as np

DANDA = "।"  # U+0964 Bengali danda


def test_length_scale_never_stretches_into_artifacts():
    from emotion.prosody import LENGTH_SCALE_MAX, LENGTH_SCALE_MIN
    from emotion.prosody import clamp_length_scale, wpm_to_length_scale

    assert LENGTH_SCALE_MIN == 0.8
    assert LENGTH_SCALE_MAX == 1.25
    # Old Bengali failure: 300 WPM calibration vs 155 target -> was 1.94.
    assert wpm_to_length_scale(300, 155) <= 1.25
    # English default: lessac natural ~199.5 vs 155 target -> was ~1.29.
    assert wpm_to_length_scale(199.5, 155) <= 1.25
    # Sane mappings untouched.
    assert wpm_to_length_scale(150, 155) == clamp_length_scale(150 / 155)
    assert clamp_length_scale(0.5) == 0.8
    assert clamp_length_scale(2.5) == 1.25
    assert clamp_length_scale(1.0) == 1.0


def test_gemini_natural_wpm_caches_and_clamps(monkeypatch, tmp_path):
    from tts.providers.gemini_provider import GeminiTTSProvider

    provider = GeminiTTSProvider("k")
    calls = {"n": 0}

    def fake_synth(text, out_path, voice_id, emotion="NEUTRAL",
                   preset_key="DOCUMENTARY", intensity=0.7):
        from tts.base import SynthesisResult

        calls["n"] += 1
        import soundfile as sf

        sr = 24000
        dur = 4.0
        t = np.linspace(0, dur, int(dur * sr), endpoint=False)
        sf.write(str(out_path),
                 (0.2 * np.sin(2 * np.pi * 200 * t)).astype(np.float32), sr)
        words = len(text.split())
        return SynthesisResult(audio_path=out_path, duration_seconds=dur,
                               sample_rate=sr, word_count=words,
                               actual_wpm=round(words / dur * 60.0, 2),
                               length_scale_used=1.0)

    monkeypatch.setattr(provider, "synthesize_with_style", fake_synth)
    # Calibration text ~38 words in 4s -> ~570 WPM -> clamped to 300.
    first = provider.natural_wpm("Charon")
    second = provider.natural_wpm("Charon")
    assert first == 300.0
    assert calls["n"] == 1  # second call served from cache


def test_bengali_paragraph_splits_into_sentences():
    from script.chunker import _split_sentences

    text = ("একদা এক গ্রামে এক কৃষক বাস করত" + DANDA +
            " সে প্রতিদিন ভোরে মাঠে যেত" + DANDA +
            " তার একটি ছোট্ট কুঁড়েঘর ছিল" + DANDA)
    sentences = _split_sentences(text)
    assert len(sentences) == 3, sentences


def test_analyzer_splits_bengali_sentences():
    from emotion.analyzer import SENTENCE_SPLIT_RE

    text = "সে ভয় পেল" + DANDA + " অন্ধকারে কে যেন হাঁটছিল" + DANDA
    assert len(SENTENCE_SPLIT_RE.split(text)) == 2


def test_voice_micro_fades_remove_edge_discontinuity():
    from audio.mixer.mixdown import _micro_fades

    rate = 44100
    burst = np.full(rate, 0.5, dtype=np.float32)  # worst case: full-level DC
    faded = _micro_fades(burst.copy(), rate)
    assert abs(float(faded[0])) < 1e-6
    assert abs(float(faded[-1])) < 1e-6
    # Body of the chunk untouched.
    assert np.allclose(faded[rate // 2], 0.5)


def test_bengali_cue_emotions():
    from emotion.analyzer import analyze_sentence

    assert analyze_sentence("সে ভয়ে কাঁপছিল।").emotion == "FEAR"
    assert analyze_sentence("তারা আনন্দে হেসে উঠল।").emotion == "HAPPY"
    assert analyze_sentence("সে রাগে গর্জন করল।").emotion == "ANGRY"
    assert analyze_sentence("মেয়েটি কাঁদতে লাগল।").emotion == "SAD"


def test_bengali_dialogue_and_questions():
    from emotion.analyzer import analyze_sentence

    dialogue = analyze_sentence("রহিম বলল, তুমি এসো।")
    assert dialogue.is_dialogue
    assert analyze_sentence("তুমি কোথায় যাচ্ছ?").emotion == "MYSTERIOUS"
    assert analyze_sentence("সে ফিসফিস করে বলল।").emotion == "WHISPER"


def test_effect_close_tags_scope_spans():
    from script.markup import parse_markup

    parsed = parse_markup("[EMPHASIS]key words[/EMPHASIS] then normal.")
    assert parsed.segments[0].effects == frozenset({"emphasis"})
    assert parsed.segments[1].effects == frozenset()
    assert "key words" in parsed.segments[0].text


def test_whisper_annotation_is_scoped():
    from emotion.analyzer import annotate_script

    annotated = annotate_script("He whispered softly. The room was silent.")
    assert "[WHISPER]" in annotated
    assert "[/WHISPER]" in annotated


def test_emphasis_span_becomes_own_chunk_with_gain():
    from app.core.generator import _chunk_gain
    from script.chunker import build_chunks
    from script.markup import parse_markup

    parsed = parse_markup("[EMPHASIS]key words here[/EMPHASIS] then normal.")
    chunks = build_chunks(parsed, target_wpm=150, voice="test")
    assert chunks[0].effects == frozenset({"emphasis"})
    assert _chunk_gain(chunks[0]) == 1.5
    assert _chunk_gain(chunks[-1]) == 0.0


def test_breath_pause_floor_is_deterministic():
    from script.chunker import build_chunks
    from script.markup import parse_markup

    def pauses():
        chunks = build_chunks(parse_markup("First sentence. Second one."),
                              target_wpm=150, voice="test")
        return [c.pause_after for c in chunks]

    first, second = pauses(), pauses()
    assert first == second  # stable across runs (cache-safe)
    assert first
    assert all(0.29 <= p <= 0.41 for p in first)


def test_cache_key_covers_effects():
    from project.cache import chunk_cache_key

    base = dict(text="Hello world", voice_id="v", engine="gemini",
                length_scale=1.0, wpm_target=155, emotion="NEUTRAL")
    assert chunk_cache_key(**base) != chunk_cache_key(
        **{**base, "effects": ("emphasis",)})
    assert chunk_cache_key(**base) == chunk_cache_key(**base)


def test_chunk_synth_is_deterministic_and_cached(tmp_path):
    import soundfile as sf

    from app.core.generator import GenerationOptions, GenerationPipeline
    from script.chunker import Chunk
    from tts.base import SynthesisResult

    class _StubTTS:
        def __init__(self) -> None:
            self.calls = 0

        def synthesize(self, text, out_path, voice_id, length_scale=1.0):
            self.calls += 1
            sr = 24000
            dur = max(0.2, len(text.split()) / 150.0 * 60.0)
            t = np.linspace(0, dur, int(dur * sr), endpoint=False)
            sf.write(str(out_path),
                     (0.3 * np.sin(2 * np.pi * 300 * t)).astype(np.float32),
                     sr)
            words = len(text.split())
            return SynthesisResult(
                audio_path=out_path, duration_seconds=dur, sample_rate=sr,
                word_count=words, actual_wpm=round(words / dur * 60.0, 2),
                length_scale_used=length_scale)

    options = GenerationOptions(voice_id="Charon", auto_emotion=False)
    pipeline = GenerationPipeline("CacheTest", tmp_path, options)
    stub = _StubTTS()
    chunk = Chunk(chunk_id=0, scene_id=1, scene_title="S", index_in_scene=0,
                  text="The quick brown fox jumps over the lazy dog",
                  wpm_target=155)
    first = pipeline._synthesize_chunk(stub, chunk)
    second = pipeline._synthesize_chunk(stub, chunk)
    assert first == second  # second served from cache: deterministic
    assert stub.calls == 1  # cloud API must not be billed twice
    import wave

    with wave.open(str(first), "rb") as wf:
        dur = wf.getnframes() / wf.getframerate()
    # 9 words at ~150 WPM ~= 3.6s.
    assert 3.4 < dur < 3.8
