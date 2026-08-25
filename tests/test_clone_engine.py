"""Tests for the optional voice-clone engine (validation + e2e if pack)."""
from __future__ import annotations

import soundfile as sf
import pytest

from audio.clone import engine


def write_wav(path, seconds: float, sr: int = 16000) -> None:
    import numpy as np
    n = int(sr * seconds)
    data = (0.3 * np.sin(2 * np.pi * 220 * np.arange(n) / sr)).astype("float32")
    sf.write(str(path), data, sr)


def test_status_text_always_returns_message(tmp_path):
    text = engine.status_text()
    assert isinstance(text, str) and text


def test_load_reference_rejects_unknown_suffix(tmp_path):
    bad = tmp_path / "ref.txt"
    bad.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError):
        engine.load_reference(str(bad))


def test_load_reference_rejects_missing_file(tmp_path):
    with pytest.raises(ValueError):
        engine.load_reference(str(tmp_path / "nope.wav"))


def test_load_reference_rejects_short_clip(tmp_path):
    short = tmp_path / "short.wav"
    write_wav(short, 1.0)
    with pytest.raises(ValueError):
        engine.load_reference(str(short))


def test_load_reference_accepts_long_enough_clip(tmp_path):
    ok = tmp_path / "ok.wav"
    write_wav(ok, 3.0)
    resolved = engine.load_reference(str(ok))
    assert resolved == ok


def test_convert_audio_end_to_end(tmp_path):
    if not engine.is_ready():
        pytest.skip("voice clone pack not installed")
    from tts.providers.piper_provider import PiperProvider

    src_path = tmp_path / "src.wav"
    provider = PiperProvider()
    provider.synthesize("এটা একটা পরীক্ষা।", src_path,
                        "bn_BD-google-medium", speaker_id=12)
    audio, sr = sf.read(str(src_path), dtype="float32")

    ref = tmp_path / "ref.wav"
    write_wav(ref, 4.0, sr=24000)
    out, out_sr = engine.convert_audio(audio, sr, ref)
    assert out_sr == sr
    assert len(out) == len(audio)
