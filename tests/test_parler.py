"""Tests for the Parler transformer provider (mocked weights)."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from app.utils.errors import UserFacingError


def _ensure_clone_libs_on_path() -> None:
    """Mirror production: torch/transformers resolve from clone_libs."""
    import sys
    from pathlib import Path

    libs = str(Path(__file__).resolve().parents[1] / "clone_libs")
    if libs not in sys.path:
        sys.path.append(libs)


_ensure_clone_libs_on_path()


def _torch_usable() -> bool:
    try:
        import torch

        return hasattr(torch, "no_grad")
    except Exception:  # noqa: BLE001 - torch needs py3.11 + clone_libs
        return False


needs_torch = pytest.mark.skipif(
    not _torch_usable(), reason="torch not importable in this interpreter")


class _FakeArray:
    def __init__(self, data: np.ndarray) -> None:
        self._data = data

    def cpu(self):
        return self

    def numpy(self):
        return self._data


class _FakeModel:
    def __init__(self, seconds: float = 1.0, rate: int = 44100) -> None:
        n = int(seconds * rate)
        t = np.linspace(0, seconds, n, endpoint=False)
        self.audio = (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
        self.config = SimpleNamespace(
            audio_encoder=SimpleNamespace(sampling_rate=rate),
            text_encoder=SimpleNamespace(_name_or_path="."),
        )
        self.calls = 0

    def generate(self, **kwargs):
        self.calls += 1
        assert "input_ids" in kwargs and "prompt_input_ids" in kwargs
        return _FakeArray(self.audio)


def _fake_tok(text, return_tensors=None):
    return SimpleNamespace(input_ids=[[1, 2]], attention_mask=[[1, 1]])


def _provider_with_fake():
    from tts.providers.parler_provider import ParlerTTSProvider

    provider = ParlerTTSProvider()
    fake = _FakeModel()
    provider._model = fake
    provider._tokenizer = _fake_tok
    provider._desc_tokenizer = _fake_tok
    provider._sample_rate = 44100
    provider._loaded_repo = "ai4bharat/indic-parler-tts"
    return provider, fake


def test_description_prompts():
    from tts.providers.parler_provider import description_for_voice

    female = description_for_voice("parler-bn-female", "SAD", 1.1)
    assert "female" in female and "Bengali" in female
    assert "sad" in female and "slowly" in female
    male = description_for_voice("parler-bn-male", "NEUTRAL", 1.0)
    assert "male" in male and "moderate pace" in male
    fast = description_for_voice("parler-bn-female", "EXCITED", 0.9)
    assert "quickly" in fast


@needs_torch
def test_synthesize_with_fake_model(tmp_path):
    provider, fake = _provider_with_fake()
    out = tmp_path / "parler.wav"
    result = provider.synthesize("hello world test", out, "parler-bn-female")
    assert out.exists()
    assert fake.calls == 1
    assert result.sample_rate == 44100
    assert result.duration_seconds == pytest.approx(1.0, abs=0.05)
    assert result.word_count == 3


@needs_torch
def test_synthesize_with_emotion_uses_tone(tmp_path):
    from tts.providers.parler_provider import description_for_voice

    provider, fake = _provider_with_fake()
    out = tmp_path / "emo.wav"
    result = provider.synthesize_with_emotion(
        "hello world", out, "parler-bn-female", "HORROR")
    assert out.exists() and result.duration_seconds > 0
    assert "ominous" in description_for_voice("parler-bn-female", "HORROR")


def test_missing_model_raises_friendly_error(tmp_path):
    from tts.providers.parler_provider import ParlerTTSProvider

    provider = ParlerTTSProvider()
    with pytest.raises(UserFacingError):
        provider.synthesize("hi", tmp_path / "x.wav", "parler-bn-female")


def test_manager_routes_parler():
    from tts.manager import available_engines, get_provider
    from tts.providers.parler_provider import ParlerTTSProvider

    assert "parler" in available_engines()
    assert isinstance(get_provider("parler"), ParlerTTSProvider)
    assert get_provider("parler").supports_emotion() is True


def test_parler_voices_in_catalog():
    from tts.voices.catalog import get_voice, parler_repo

    for vid in ("parler-bn-female", "parler-bn-male"):
        info = get_voice(vid)
        assert info is not None and info.engine == "parler"
        assert info.commercial_use is True
        assert "Apache" in info.license
    assert parler_repo("parler-bn-female") == "ai4bharat/indic-parler-tts"
    assert parler_repo("en_US-lessac-medium") is None


def test_parler_not_installed_without_files():
    from models.downloader import is_voice_installed

    assert is_voice_installed("parler-bn-female") is False


def test_install_parler_requires_token():
    from models.downloader import install_voice

    with pytest.raises(UserFacingError) as exc:
        install_voice("parler-bn-female", None, "")
    assert "token" in str(exc.value.what).lower()
