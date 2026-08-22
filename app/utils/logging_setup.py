"""Rotating file + console logging.

Log files: app.log, tts.log, audio.log, render.log, error.log under the
user data logs directory.
"""
from __future__ import annotations

import logging
import logging.handlers
import sys

from app.config.paths import logs_dir

_FORMAT = "%(asctime)s %(levelname)-7s [%(name)s] %(message)s"
_loggers_configured: set[str] = set()


def _make_file_handler(name: str) -> logging.Handler:
    path = logs_dir() / f"{name}.log"
    handler = logging.handlers.RotatingFileHandler(
        path, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(_FORMAT))
    return handler


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if getattr(root, "_storyvoice_configured", False):
        return
    root.setLevel(level)
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(logging.Formatter("%(levelname)-7s %(name)s: %(message)s"))
    root.addHandler(console)

    error_handler = _make_file_handler("error")
    error_handler.setLevel(logging.ERROR)
    root.addHandler(error_handler)

    for logger_name, file_name in (
        ("app", "app"),
        ("tts", "tts"),
        ("audio", "audio"),
        ("render", "render"),
    ):
        lg = logging.getLogger(logger_name)
        lg.addHandler(_make_file_handler(file_name))
        _loggers_configured.add(logger_name)

    root._storyvoice_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def open_logs_folder() -> str:
    return str(logs_dir())
