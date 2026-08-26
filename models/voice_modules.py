"""Saved voice-clone modules: reference clips + metadata."""
from __future__ import annotations

import json
import logging
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path

from app.config.paths import voice_modules_dir

log = logging.getLogger("app")

MODULES_FILE = "modules.json"


@dataclass
class VoiceModule:
    name: str
    reference_filename: str
    created_at: str = ""
    tau: float = 0.3


def _modules_path() -> Path:
    return voice_modules_dir() / MODULES_FILE


def load_modules() -> list[VoiceModule]:
    path = _modules_path()
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [VoiceModule(**m) for m in raw if isinstance(m, dict)]
    except Exception:
        log.warning("Corrupt voice_modules.json, resetting", exc_info=True)
        return []


def _save_modules(modules: list[VoiceModule]) -> None:
    path = _modules_path()
    path.write_text(
        json.dumps([asdict(m) for m in modules], indent=2),
        encoding="utf-8",
    )


def save_module(name: str, source_ref: Path, tau: float = 0.3) -> VoiceModule:
    from datetime import datetime, timezone

    modules = load_modules()
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in name).strip("_")
    if not slug:
        raise ValueError("Module name must not be empty.")
    if any(m.name == name for m in modules):
        raise ValueError(f"A module named '{name}' already exists.")

    module_dir = voice_modules_dir() / slug
    module_dir.mkdir(parents=True, exist_ok=True)
    dest = module_dir / source_ref.name
    shutil.copy2(str(source_ref), str(dest))

    module = VoiceModule(
        name=name,
        reference_filename=dest.name,
        created_at=datetime.now(timezone.utc).isoformat(),
        tau=tau,
    )
    modules.append(module)
    _save_modules(modules)
    log.info("Saved voice module '%s' -> %s", name, dest)
    return module


def delete_module(name: str) -> bool:
    modules = load_modules()
    before = len(modules)
    modules = [m for m in modules if m.name != name]
    if len(modules) == before:
        return False
    _save_modules(modules)
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in name).strip("_")
    module_dir = voice_modules_dir() / slug
    if module_dir.exists():
        shutil.rmtree(module_dir, ignore_errors=True)
    log.info("Deleted voice module '%s'", name)
    return True


def module_ref_path(name: str) -> Path | None:
    modules = load_modules()
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in name).strip("_")
    for m in modules:
        if m.name == name:
            p = voice_modules_dir() / slug / m.reference_filename
            return p if p.exists() else None
    return None


def module_tau(name: str) -> float:
    modules = load_modules()
    for m in modules:
        if m.name == name:
            return m.tau
    return 0.3