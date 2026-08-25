"""Filesystem locations for user data, logs, models and cache."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "StoryVoiceStudio"


def _base_data_dir() -> Path:
    """Heavy data (models/cache/logs) lives outside C: when possible.

    Priority:
    1. STORYVOICE_DATA_DIR environment variable
    2. When run from source: <repo>/userdata (keeps everything portable,
       e.g. on G: where the project lives)
    3. Frozen builds: %LOCALAPPDATA%/StoryVoiceStudio
    """
    override = os.environ.get("STORYVOICE_DATA_DIR")
    if override:
        return Path(override)
    if not getattr(sys, "frozen", False):
        # app/config/paths.py -> [0]=config [1]=app [2]=repo root
        return Path(__file__).resolve().parents[2] / "userdata"
    local = os.environ.get("LOCALAPPDATA")
    base = Path(local) if local else Path.home() / "AppData" / "Local"
    return base / APP_DIR_NAME


def data_dir() -> Path:
    path = _base_data_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def settings_file() -> Path:
    return data_dir() / "settings.json"


def models_dir() -> Path:
    path = data_dir() / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def clone_models_dir() -> Path:
    """Checkpoints for the optional OpenVoice tone-cloning pack."""
    path = models_dir() / "openvoice"
    path.mkdir(parents=True, exist_ok=True)
    return path


def references_dir() -> Path:
    """Downloaded/uploaded voice-clone reference clips."""
    path = data_dir() / "references"
    path.mkdir(parents=True, exist_ok=True)
    return path


def voices_dir() -> Path:
    path = models_dir() / "voices"
    path.mkdir(parents=True, exist_ok=True)
    return path


def projects_dir() -> Path:
    # Projects hold large audio caches - keep them on the same drive as
    # the rest of the user data (G: when run from source).
    path = data_dir() / "Projects"
    path.mkdir(parents=True, exist_ok=True)
    return path


def audio_cache_root() -> Path:
    path = data_dir() / "cache" / "chunks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def analysis_cache_dir() -> Path:
    path = data_dir() / "cache" / "analysis"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logs_dir() -> Path:
    path = data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def exports_dir() -> Path:
    """User-facing output folder: Downloads\\StoryVoiceStudio."""
    path = Path.home() / "Downloads" / "StoryVoiceStudio"
    path.mkdir(parents=True, exist_ok=True)
    return path


def repo_asset_dir(*parts: str) -> Path:
    """Locate read-only bundled assets, both in dev tree and frozen builds."""
    if getattr(sys, "frozen", False):
        root = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        root = Path(__file__).resolve().parents[2]
    path = root.joinpath("assets", *parts)
    return path


def sanitize_project_path(base: Path, name: str) -> Path:
    """Join *name* under *base*, rejecting path traversal and invalid names."""
    name = (name or "").strip()
    if not name:
        raise ValueError("Project name must not be empty.")
    bad = set('<>:"/\\|?*') | {chr(c) for c in range(32)}
    cleaned = "".join("_" if ch in bad else ch for ch in name).rstrip(" .")
    candidate = (base / cleaned).resolve()
    base_resolved = base.resolve()
    if not str(candidate).startswith(str(base_resolved)):
        raise ValueError("Invalid project path.")
    return candidate
