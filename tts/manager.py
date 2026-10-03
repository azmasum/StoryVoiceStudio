"""TTS engine manager - selects and caches provider instances."""
from __future__ import annotations

import logging

from tts.base import TTSProvider

log = logging.getLogger("tts")

_PROVIDERS: dict[str, TTSProvider] = {}

# Removed local engines keep working by mapping onto the free default,
# so projects/settings saved by older app versions never crash.
LEGACY_ENGINES = {"piper": "edge", "parler": "edge"}


def resolve_engine(engine: str | None) -> str:
    """Normalize an engine name; legacy local engines map to edge."""
    key = (engine or "edge").lower()
    if key in LEGACY_ENGINES:
        log.info("Mapping legacy TTS engine '%s' to '%s'", key,
                 LEGACY_ENGINES[key])
        return LEGACY_ENGINES[key]
    return key


def available_engines() -> list[str]:
    # EdgeTTS first: free and keyless. Gemini needs an API key + billing.
    return ["edge", "gemini"]


def get_provider(engine: str) -> TTSProvider:
    """Return a shared provider instance for *engine*."""
    key = resolve_engine(engine)
    if key in _PROVIDERS:
        return _PROVIDERS[key]
    if key == "edge":
        from tts.providers.edge_provider import EdgeTTSProvider

        _PROVIDERS[key] = EdgeTTSProvider()
        return _PROVIDERS[key]
    if key == "gemini":
        from tts.providers.gemini_provider import GeminiTTSProvider

        _PROVIDERS[key] = GeminiTTSProvider()
        return _PROVIDERS[key]
    raise ValueError(f"Unknown TTS engine: {engine}. Available: {available_engines()}")


def reset_provider(engine: str) -> None:
    """Unload a cached provider (used when settings change)."""
    provider = _PROVIDERS.pop(resolve_engine(engine), None)
    if provider is not None:
        try:
            provider.unload_model()
        except Exception:  # noqa: BLE001
            log.exception("Failed to unload provider %s", engine)


def get_configured_provider() -> TTSProvider:
    """Provider wired from local settings (engine + Gemini key/model)."""
    from app.config.settings import load_settings

    settings = load_settings()
    engine = resolve_engine(settings.tts_engine)
    provider = get_provider(engine)
    if engine == "gemini" and hasattr(provider, "configure"):
        provider.configure(settings.gemini_api_key, settings.gemini_model)
    return provider
