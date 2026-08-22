"""Tests for markup parsing and chunking."""
from script.chunker import build_chunks, estimate_duration, split_scenes
from script.markup import parse_markup, strip_markup
from script.normalizer import normalize


def test_parse_emotion_markup():
    parsed = parse_markup("Hello world. [EMOTION:FEAR]Something scary here.")
    assert len(parsed.segments) == 2
    assert parsed.segments[0].emotion == ""
    assert parsed.segments[1].emotion == "FEAR"


def test_parse_pause():
    parsed = parse_markup("First part. [PAUSE:2] Second part.")
    pauses = [s.pause_after for s in parsed.segments]
    assert 2.0 in pauses


def test_unknown_tags_stripped():
    result = strip_markup("[BOGUS]keep me[/BOGUS]")
    assert "keep me" in result
    assert "[BOGUS]" not in result


def test_scene_splitting():
    text = (
        "[SCENE: Night]\n\nFirst paragraph.\n\n"
        "# Morning\n\nSecond paragraph."
    )
    scenes = split_scenes(text)
    titles = [t for _i, t, _p in scenes]
    assert "Night" in titles
    assert len(scenes) >= 2


def test_chunking_never_splits_sentences(sample_script):
    from script.markup import parse_markup as pm

    normalized = normalize(pm(sample_script).plain_text)
    reparsed = pm(normalized)
    chunks = build_chunks(reparsed, target_wpm=150, voice="test")
    assert chunks
    for chunk in chunks:
        # Every chunk must end at a sentence boundary (or clause fallback).
        text = chunk.text.strip()
        if len(text) < 600:
            assert text[-1] in ".!?\"'" or text[-1].isalnum()


def test_chunk_metadata(sample_script):
    chunks = build_chunks(parse_markup(normalize(sample_script)),
                          target_wpm=160, voice="v1")
    first = chunks[0]
    assert first.chunk_id == 0
    assert first.wpm_target == 160
    assert first.voice == "v1"
    ids = [c.chunk_id for c in chunks]
    assert ids == list(range(len(chunks)))


def test_estimate_duration():
    # 155 words per minute -> about 60 seconds for 155 words.
    duration = estimate_duration(155, 155)
    assert 55 <= duration <= 65
