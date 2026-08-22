"""Model manager: list, install, remove and report on AI models/voices."""
from __future__ import annotations

from dataclasses import dataclass

from models.downloader import (
    installed_manifest,
    install_voice,
    is_voice_installed,
    remove_voice,
    verify_installed,
)
from tts.voices.catalog import CATALOG_VOICES


@dataclass
class ModelStatus:
    model_id: str
    name: str
    version: str
    size_mb: float
    license: str
    commercial_use: bool
    source_url: str
    installed: bool
    verified: bool | None  # None = not yet checked


def list_models() -> list[ModelStatus]:
    manifest = installed_manifest()
    statuses: list[ModelStatus] = []
    for entry in CATALOG_VOICES:
        installed = entry["voice_id"] in manifest
        verified = verify_installed(entry["voice_id"]) if installed else None
        meta = manifest.get(entry["voice_id"], {})
        statuses.append(ModelStatus(
            model_id=entry["voice_id"],
            name=entry["name"],
            version=str(meta.get("version", "v1.0.0")),
            size_mb=float(meta.get("size_bytes", 0)) / (1024**2) or entry["model_size_mb"],
            license=entry["license"],
            commercial_use=bool(entry["commercial_use"]),
            source_url=str(meta.get("source", "")),
            installed=installed,
            verified=verified,
        ))
    return statuses


def ensure_default_voice(voice_id: str,
                         progress=None) -> bool:
    """Install *voice_id* if missing. Returns True when already present."""
    if is_voice_installed(voice_id):
        return True
    install_voice(voice_id, progress)
    return False


__all__ = [
    "ModelStatus",
    "list_models",
    "install_voice",
    "remove_voice",
    "is_voice_installed",
    "verify_installed",
    "ensure_default_voice",
    "installed_manifest",
]
