"""TTS provider contract tests (skipped when piper/model is unavailable)."""
from __future__ import annotations

from pathlib import Path

import pytest

from models.downloader import is_voice_installed
from tts.manager import available_engines, get_provider
from tts.voices.catalog import CATALOG_VOICES


def test_catalog_entries_have_licenses():
    for entry in CATALOG_VOICES:
        assert entry["license"]
        assert isinstance(entry["commercial_use"], bool)


def test_engines_available():
    assert "piper" in available_engines()


def _provider_or_skip():
    try:
        provider = get_provider("piper")
    except Exception as error:  # noqa: BLE001
        pytest.skip(f"piper unavailable: {error}")
    if not is_voice_installed("en_US-danny-low"):
        pytest.skip("No voice model installed - download one to run this")
    return provider


def test_synthesize_real_audio(tmp_path: Path):
    provider = _provider_or_skip()
    out = tmp_path / "chunk.wav"
    result = provider.synthesize(
        "The last train home left at midnight.", out,
        voice_id="en_US-danny-low", length_scale=1.0)
    assert out.exists() and out.stat().st_size > 1000
    assert 0.5 < result.duration_seconds < 20.0
    assert result.actual_wpm > 60


def test_natural_wpm_measurement():
    provider = _provider_or_skip()
    wpm = provider.natural_wpm("en_US-danny-low")
    assert 80 <= wpm <= 280


def test_capabilities_contract():
    provider = get_provider("piper")
    capabilities = provider.get_capabilities()
    assert not capabilities.supports_voice_cloning
    assert provider.get_license()["commercial_use"] is True
