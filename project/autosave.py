"""Automatic saving and crash-recovery snapshots."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

from project.database import StoryProject, save_project

log = logging.getLogger("app")

AUTOSAVE_SUFFIX = ".autosave.storyproj"


class AutosaveManager:
    """Writes recovery snapshots; call :meth:`maybe_autosave` from a timer."""

    def __init__(self, interval_seconds: int = 60) -> None:
        self.interval_seconds = max(15, int(interval_seconds))
        self._dirty = False
        self._last_saved_at = 0.0

    def mark_dirty(self) -> None:
        self._dirty = True

    def maybe_autosave(self, project: StoryProject, project_path: Path,
                       now: float) -> Path | None:
        import time

        if not self._dirty:
            return None
        if now - self._last_saved_at < self.interval_seconds:
            return None
        out = autosave_path(project_path)
        try:
            save_project(project, out)
            self._dirty = False
            self._last_saved_at = now
            return out
        except Exception:  # noqa: BLE001
            log.exception("Autosave failed for %s", project_path)
            return None


def autosave_path(project_path: str | Path) -> Path:
    path = Path(project_path)
    return path.with_name(path.stem + AUTOSAVE_SUFFIX)


def has_recovery_snapshot(project_path: str | Path) -> bool:
    snapshot = autosave_path(project_path)
    if not snapshot.exists():
        return False
    target = Path(project_path)
    if not target.exists():
        return True
    return snapshot.stat().st_mtime > target.stat().st_mtime


def recover(project_path: str | Path) -> Path | None:
    """Restore the newest snapshot over the saved file. Returns new path."""
    snapshot = autosave_path(project_path)
    if not snapshot.exists():
        return None
    shutil.copyfile(snapshot, project_path)
    log.info("Recovered project %s from autosave snapshot", project_path)
    return Path(project_path)


def discard_snapshot(project_path: str | Path) -> None:
    autosave_path(project_path).unlink(missing_ok=True)
