"""Optional update check against GitHub Releases.

Only runs when the user clicks "Check for Updates" or enables automatic
checking. Never blocks startup and never forces an update; the app keeps
working fully offline.
"""
from __future__ import annotations

import json
import logging
import urllib.request
from dataclasses import dataclass

from app.version import GITHUB_RELEASES_API, VERSION

log = logging.getLogger(__name__)
TIMEOUT_SECONDS = 10


@dataclass
class UpdateInfo:
    available: bool
    latest_version: str = ""
    download_url: str = ""
    release_notes: str = ""
    error: str = ""


def _version_tuple(version: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in version.lstrip("v").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts)


def _newer(candidate: str, current: str) -> bool:
    try:
        return _version_tuple(candidate) > _version_tuple(current)
    except Exception:  # noqa: BLE001
        return False


def fetch_latest_release(timeout: int = TIMEOUT_SECONDS) -> UpdateInfo:
    try:
        request = urllib.request.Request(
            GITHUB_RELEASES_API,
            headers={"Accept": "application/vnd.github+json",
                     "User-Agent": "StoryVoiceStudio"},
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        tag = str(payload.get("tag_name", "")).lstrip("v")
        assets = payload.get("assets") or []
        setup_url = next(
            (
                a["browser_download_url"]
                for a in assets
                if str(a.get("name", "")).endswith("-Setup.exe")
            ),
            "",
        )
        return UpdateInfo(
            available=_newer(tag, VERSION),
            latest_version=tag,
            download_url=setup_url,
            release_notes=str(payload.get("body", "")),
        )
    except Exception as exc:  # noqa: BLE001 - offline mode must stay silent-ish
        log.info("Update check unavailable (%s)", exc)
        return UpdateInfo(available=False, error="Offline mode enabled.")


def check_for_update() -> UpdateInfo:
    return fetch_latest_release()
