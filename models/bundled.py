"""Copy models shipped inside the app package into the user's data dir.

The Windows build bundles every catalog voice under ``models/voices``
(PyInstaller datas).  On first launch - or whenever a bundled voice is
missing locally - the files are copied to the real voices directory and
the installed-models manifest is updated, so no download is required.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

from app.config.paths import voices_dir
from models.downloader import (
    MANIFEST_NAME,
    installed_manifest,
    _write_manifest,
)

log = __import__("logging").getLogger(__name__)


def bundled_voices_dir() -> Path | None:
    """Location of the read-only model copies shipped with the app."""
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", None)
        if not base:
            return None
        candidate = Path(base) / "models" / "voices"
        return candidate if candidate.exists() else None
    # Source mode keeps models in the repo bundle folder too.
    candidate = Path(__file__).resolve().parents[1] / "models" / "voices"
    return candidate if candidate.exists() else None


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def seed_bundled_voices() -> list[str]:
    """Install any missing bundled voices; returns seeded voice ids."""
    src_root = bundled_voices_dir()
    if src_root is None:
        return []
    seeded: list[str] = []
    manifest = installed_manifest()
    manifest_dirty = False
    for folder in sorted(src_root.iterdir()):
        if not folder.is_dir():
            continue
        voice_id = folder.name
        # Validate the bundle entry fully BEFORE touching the destination,
        # so a broken entry can never leave a half-installed folder behind.
        src_files = [item for item in folder.iterdir()
                     if item.is_file() and item.suffix in {".onnx", ".json"}]
        names = {item.name for item in src_files}
        if f"{voice_id}.onnx" not in names or f"{voice_id}.onnx.json" not in names:
            log.warning("Skipping incomplete bundled voice %s", voice_id)
            continue
        dest = voices_dir() / voice_id
        if ((dest / f"{voice_id}.onnx").exists()
                and (dest / f"{voice_id}.onnx.json").exists()):
            continue
        try:
            dest.mkdir(parents=True, exist_ok=True)
            for item in src_files:
                shutil.copy2(item, dest / item.name)
            onnx = dest / f"{voice_id}.onnx"
            manifest[voice_id] = {
                "size": onnx.stat().st_size,
                "sha256": _sha256(onnx),
                "source": "bundled",
            }
            manifest_dirty = True
            seeded.append(voice_id)
            log.info("Seeded bundled voice %s", voice_id)
        except Exception:  # noqa: BLE001 - never block startup
            log.exception("Failed to seed bundled voice %s", voice_id)
    if manifest_dirty:
        _write_manifest(manifest)
    return seeded


def bundled_manifest_exists() -> bool:
    src = bundled_voices_dir()
    return bool(src and (src / MANIFEST_NAME).exists())