"""Chunk-level audio cache with content-addressed keys.

Changing one sentence regenerates only that chunk; unchanged chunks are
reused from cache, which also powers resume-after-crash behavior.
"""
from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path

log = logging.getLogger("render")


def chunk_cache_key(
    text: str,
    voice_id: str,
    engine: str,
    length_scale: float,
    wpm_target: int,
    emotion: str,
) -> str:
    payload = json.dumps(
        {
            "text": text,
            "voice": voice_id,
            "engine": engine,
            "scale": round(length_scale, 5),
            "wpm": wpm_target,
            "emotion": emotion,
        },
        sort_keys=True,
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:24]


class ChunkCache:
    """Stores rendered chunks as ``<key>.wav`` inside a project cache dir."""

    def __init__(self, cache_dir: str | Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, key: str) -> Path:
        return self.cache_dir / f"{key}.wav"

    def get(self, key: str) -> Path | None:
        path = self.path_for(key)
        if path.exists() and path.stat().st_size > 44:
            return path
        if path.exists():
            path.unlink(missing_ok=True)
        return None

    def put(self, key: str, source_path: Path) -> Path:
        dest = self.path_for(key)
        source_path.replace(dest)
        return dest

    def clear(self) -> int:
        removed = 0
        for wav in self.cache_dir.glob("*.wav"):
            try:
                wav.unlink()
                removed += 1
            except OSError:
                log.warning("Could not remove cached file %s", wav)
        return removed

    def size_bytes(self) -> int:
        return sum(f.stat().st_size for f in self.cache_dir.glob("*") if f.is_file())
