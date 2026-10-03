"""Persistent application settings (JSON file under the user data directory)."""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from app.config.paths import settings_file

log = logging.getLogger(__name__)


@dataclass
class AppSettings:
    # General
    simple_mode: bool = True
    autosave_seconds: int = 60
    default_project_dir: str = ""

    # TTS: "edge" (free, keyless) or "gemini" (API key + billing).
    tts_engine: str = "edge"
    voice_id: str = "en-US-AriaNeural"
    voice_lock: bool = True
    # Gemini API key from https://aistudio.google.com/apikey.
    # Stored in the local settings file only, never logged or transmitted
    # anywhere except generativelanguage.googleapis.com.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-pro-preview-tts"
    dialogue_voice: str = "en-US-GuyNeural"

    # Performance
    prefer_gpu: bool = True
    max_chunk_seconds: float = 25.0

    # Audio defaults
    target_wpm: int = 155
    emotion_intensity: float = 0.7
    loudness_preset: str = "YouTube"
    custom_lufs: float = -14.0
    ducking_db: float = 9.0
    ducking_attack_ms: int = 200
    ducking_release_ms: int = 300
    music_gain_db: float = -18.0

    # Export
    export_format: str = "wav"
    export_stems: bool = False

    # Privacy / updates
    telemetry: bool = False  # always off; reserved for explicit opt-in only
    auto_update_check: bool = False
    last_seen_version: str = ""
    first_run_done: bool = False

    extra: dict[str, Any] = field(default_factory=dict)


def load_settings() -> AppSettings:
    path: Path = settings_file()
    if not path.exists():
        return AppSettings()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        known = {f.name for f in fields(AppSettings)}
        filtered = {k: v for k, v in raw.items() if k in known}
        settings = AppSettings(**filtered)
    except Exception:  # noqa: BLE001 - corrupt settings must not crash startup
        log.exception("Failed to read settings; using defaults")
        return AppSettings()
    # Migrate engines removed in v0.2+ (piper/parler -> edge).
    from tts.manager import available_engines, resolve_engine

    engine = resolve_engine(settings.tts_engine)
    settings.tts_engine = (engine if engine in available_engines()
                           else "edge")
    return settings


def save_settings(settings: AppSettings) -> None:
    path: Path = settings_file()
    try:
        path.write_text(
            json.dumps(asdict(settings), indent=2), encoding="utf-8"
        )
    except Exception:  # noqa: BLE001
        log.exception("Failed to save settings to %s", path)
