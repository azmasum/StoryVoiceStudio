"""TTS provider contract tests (EdgeTTS default, Gemini optional)."""
from __future__ import annotations

import pytest

from tts.manager import available_engines, get_provider


def test_only_gemini_engine_registered():
    assert available_engines() == ["edge", "gemini"]
    provider = get_provider("edge")
    assert provider.name == "edge"
    assert provider.is_loaded() is True


def test_unknown_engine_rejected():
    with pytest.raises(ValueError):
        get_provider("definitely-not-an-engine")


def test_legacy_engines_map_to_edge():
    from tts.manager import resolve_engine
    from tts.providers.edge_provider import EdgeTTSProvider

    assert resolve_engine("piper") == "edge"
    assert resolve_engine("parler") == "edge"
    assert resolve_engine("gemini") == "gemini"
    assert isinstance(get_provider("piper"), EdgeTTSProvider)


def test_voice_catalog_lists_both_engines():
    from tts.voices.catalog import CATALOG_VOICES

    assert len(CATALOG_VOICES) == 38  # 8 EdgeTTS + 30 Gemini
    assert {e["engine"] for e in CATALOG_VOICES} == {"edge", "gemini"}


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

    save_settings(AppSettings(tts_engine="gemini", gemini_api_key="abc123",
                              gemini_model="gemini-2.5-flash-preview-tts"))
    provider = get_configured_provider()
    assert provider.name == "gemini"
    assert provider._api_key == "abc123"
    assert provider._model == "gemini-2.5-flash-preview-tts"
    reset_provider("gemini")


def test_configured_provider_defaults_to_edge(monkeypatch, tmp_path):
    from app.config import settings as settings_module
    from tts.manager import get_configured_provider, reset_provider

    reset_provider("edge")
    monkeypatch.setattr(settings_module, "settings_file",
                        lambda: tmp_path / "settings.json")
    from app.config.settings import AppSettings, save_settings

    save_settings(AppSettings())
    provider = get_configured_provider()
    assert provider.name == "edge"
    reset_provider("edge")
