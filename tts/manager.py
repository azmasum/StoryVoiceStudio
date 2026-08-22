"""TTS engine manager - selects and caches provider instances."""
from __future__ import annotations

import logging

from tts.base import TTSProvider

log = logging.getLogger("tts")

_PROVIDERS: dict[str, TTSProvider] = {}


def available_engines() -> list[str]:
    engines = ["piper"]
    return engines


def get_provider(engine: str) -> TTSProvider:
    """Return a shared provider instance for *engine*."""
    key = engine.lower()
    if key in _PROVIDERS:
        return _PROVIDERS[key]
    if key == "piper":
        from tts.providers.piper_provider import PiperProvider

        _PROVIDERS[key] = PiperProvider()
        return _PROVIDERS[key]
    raise ValueError(f"Unknown TTS engine: {engine}. Available: {available_engines()}")


def reset_provider(engine: str) -> None:
    """Unload a cached provider (used when models change on disk)."""
    provider = _PROVIDERS.pop(engine.lower(), None)
    if provider is not None:
        try:
            provider.unload_model()
        except Exception:  # noqa: BLE001
            log.exception("Failed to unload provider %s", engine)
