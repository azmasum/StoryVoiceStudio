"""TTS provider contract tests (Gemini cloud voices, network mocked)."""
from __future__ import annotations

import pytest

from tts.manager import available_engines, get_provider


def test_only_gemini_engine_registered():
    assert available_engines() == ["gemini"]
    provider = get_provider("gemini")
    assert provider.name == "gemini"
    assert provider.is_loaded() is True


def test_unknown_engine_rejected():
    with pytest.raises(ValueError):
        get_provider("piper")


def test_voice_catalog_lists_thirty():
    from tts.voices.catalog import CATALOG_VOICES

    assert len(CATALOG_VOICES) == 30
    assert {e["engine"] for e in CATALOG_VOICES} == {"gemini"}


def test_provider_capabilities():
    provider = get_provider("gemini")
    assert provider.supports_emotion() is True
    assert provider.supports_voice_cloning() is False
    assert provider.get_capabilities().supports_emotion_natively is True
    license_info = provider.get_license()
    assert "Gemini" in license_info["engine"]
    assert provider.estimate_duration("one two three", "Charon", 150) > 0


def test_configured_provider_reads_settings(monkeypatch, tmp_path):
    from app.config import settings as settings_module
    from tts.manager import get_configured_provider, reset_provider

    reset_provider("gemini")
    monkeypatch.setattr(settings_module, "settings_file",
                        lambda: tmp_path / "settings.json")
    from app.config.settings import AppSettings, save_settings

    save_settings(AppSettings(gemini_api_key="abc123",
                              gemini_model="gemini-2.5-flash-preview-tts"))
    provider = get_configured_provider()
    assert provider._api_key == "abc123"
    assert provider._model == "gemini-2.5-flash-preview-tts"
    reset_provider("gemini")
