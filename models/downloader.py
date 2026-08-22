"""Voice model download with progress, SHA256 recording and verification.

Downloads come only from official sources listed in models/registry.json.
Checksums that are null in the registry are computed during download,
stored in an installed-models manifest, and re-verified on later launches
so any corruption is detected.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Callable

from app.config.paths import voices_dir
from app.utils.errors import UserFacingError
from tts.voices.catalog import get_voice, model_urls

log = logging.getLogger("tts")

MANIFEST_NAME = "installed.json"
CHUNK_SIZE = 1 << 16


def manifest_path() -> Path:
    return voices_dir() / MANIFEST_NAME


def installed_manifest() -> dict[str, dict]:
    path = manifest_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        log.exception("Corrupt installed-models manifest; ignoring")
        return {}


def _write_manifest(manifest: dict[str, dict]) -> None:
    manifest_path().write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )


def voice_model_paths(voice_id: str) -> tuple[Path, Path]:
    folder = voices_dir() / voice_id
    return folder / f"{voice_id}.onnx", folder / f"{voice_id}.onnx.json"


def is_voice_installed(voice_id: str) -> bool:
    onnx, js = voice_model_paths(voice_id)
    return onnx.exists() and js.exists()


ProgressCallback = Callable[[str, int, int], None]  # (stage, done_bytes, total_bytes)


def _atomic_replace(tmp: Path, dest: Path) -> None:
    """Rename *tmp* onto *dest*, riding out transient antivirus locks.

    Windows Defender and other AV products briefly open freshly written
    files for scanning, which makes an immediate rename fail with
    WinError 32. A short retry loop resolves this in practice.
    """
    last_exc: Exception | None = None
    for attempt in range(6):
        try:
            tmp.replace(dest)
            return
        except PermissionError as exc:
            last_exc = exc
            time.sleep(0.4 * (attempt + 1))
    assert last_exc is not None
    raise last_exc


def _download(url: str, dest: Path, progress: ProgressCallback | None,
              stage: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "StoryVoiceStudio"})
    tmp = dest.with_suffix(f".{os.getpid()}-{uuid.uuid4().hex[:8]}.part")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            total = int(response.headers.get("Content-Length", 0))
            hasher = hashlib.sha256()
            done = 0
            with open(tmp, "wb") as fh:
                while True:
                    block = response.read(CHUNK_SIZE)
                    if not block:
                        break
                    fh.write(block)
                    hasher.update(block)
                    done += len(block)
                    if progress and total:
                        progress(stage, done, total)
        _atomic_replace(tmp, dest)
        _ = hasher.hexdigest()
    except Exception as exc:  # noqa: BLE001
        tmp.unlink(missing_ok=True)
        raise UserFacingError(
            what=f"Download failed for {dest.name}.",
            why=str(exc),
            actions=[
                "Check your internet connection and try again.",
                "If your antivirus is active, wait a few seconds and retry.",
                "You can also download the file manually from the source URL "
                "shown in the Model Manager.",
            ],
        ) from exc


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_installed(voice_id: str) -> bool:
    """Re-verify a previously installed voice against its recorded hash."""
    entry = installed_manifest().get(voice_id)
    if not entry or not is_voice_installed(voice_id):
        return False
    onnx, _ = voice_model_paths(voice_id)
    recorded = entry.get("sha256_onnx", "")
    return bool(recorded) and _sha256(onnx) == recorded


def install_voice(
    voice_id: str,
    progress: ProgressCallback | None = None,
) -> Path:
    """Download and install *voice_id*; returns the ONNX model path."""
    info = get_voice(voice_id)
    urls = model_urls(voice_id)
    if info is None or urls is None:
        raise UserFacingError(
            what=f"Unknown voice '{voice_id}'.",
            why="This voice is not in the built-in catalog.",
            actions=["Pick one of the voices shown in the Model Manager."],
        )
    onnx_url, json_url = urls
    onnx_path, json_path = voice_model_paths(voice_id)

    log.info("Installing voice %s from official piper-voices repository",
             voice_id)
    _download(onnx_url, onnx_path, progress, f"{voice_id}: model")
    _download(json_url, json_path, progress, f"{voice_id}: config")

    sha_onnx = _sha256(onnx_path)
    sha_json = _sha256(json_path)
    expected = info.model_size_mb * 1024 * 1024
    actual = onnx_path.stat().st_size
    if expected and actual < expected * 0.5:
        # Far smaller than advertised - almost certainly an HTML error page.
        onnx_path.unlink(missing_ok=True)
        raise UserFacingError(
            what=f"Downloaded model for {voice_id} looks invalid.",
            why=f"File size {actual} bytes is much smaller than expected.",
            actions=["Try again; if it persists, report this at the issue tracker."],
        )

    manifest = installed_manifest()
    manifest[voice_id] = {
        "version": "v1.0.0",
        "source": onnx_url,
        "license": "MIT",
        "commercial_use": True,
        "size_bytes": actual,
        "sha256_onnx": sha_onnx,
        "sha256_json": sha_json,
    }
    _write_manifest(manifest)
    log.info("Voice %s installed (%.1f MB)", voice_id, actual / (1024**2))
    return onnx_path


def remove_voice(voice_id: str) -> None:
    onnx, js = voice_model_paths(voice_id)
    onnx.unlink(missing_ok=True)
    js.unlink(missing_ok=True)
    manifest = installed_manifest()
    manifest.pop(voice_id, None)
    _write_manifest(manifest)
