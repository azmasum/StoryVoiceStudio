"""TTS engine manager - selects and caches provider instances."""
from __future__ import annotations

import logging

from tts.base import TTSProvider

log = logging.getLogger("tts")

_PROVIDERS: dict[str, TTSProvider] = {}


def available_engines() -> list[str]:
    return ["gemini"]


def get_provider(engine: str) -> TTSProvider:
    """Return a shared provider instance for *engine*."""
    key = (engine or "gemini").lower()
    if key in _PROVIDERS:
        return _PROVIDERS[key]
    if key == "gemini":
        from tts.providers.gemini_provider import GeminiTTSProvider

        _PROVIDERS[key] = GeminiTTSProvider()
        return _PROVIDERS[key]
    raise ValueError(f"Unknown TTS engine: {engine}. Available: {available_engines()}")


def reset_provider(engine: str) -> None:
    """Unload a cached provider (used when settings change)."""
    provider = _PROVIDERS.pop((engine or "gemini").lower(), None)
    if provider is not None:
        try:
            provider.unload_model()
        except Exception:  # noqa: BLE001
            log.exception("Failed to unload provider %s", engine)


def get_configured_provider() -> TTSProvider:
    """Provider wired with the API key + model from local settings."""
    from app.config.settings import load_settings

    settings = load_settings()
    provider = get_provider("gemini")
    if hasattr(provider, "configure"):
        provider.configure(settings.gemini_api_key, settings.gemini_model)
    return provider
