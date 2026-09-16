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


def test_bengali_voice_calibrates_with_bengali_text():
    from tts.providers.piper_provider import _calibration_text

    bn = _calibration_text("bn_BD-google-medium")
    assert DANDA in bn  # Bengali passage, not the English one
    en = _calibration_text("en_US-lessac-medium")
    assert DANDA not in en
    assert "house" in en


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
