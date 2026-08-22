"""Crash-recovery helpers and generation history (SQLite)."""
from __future__ import annotations

import json
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from app.config.paths import data_dir
from project.autosave import (
    AutosaveManager,
    autosave_path,
    discard_snapshot,
    has_recovery_snapshot,
    recover,
)

log = logging.getLogger("app")

DB_NAME = "history.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT NOT NULL,
    project_path TEXT NOT NULL,
    output_path TEXT NOT NULL,
    duration_seconds REAL,
    word_count INTEGER,
    voice_id TEXT,
    wpm_target INTEGER,
    lufs REAL,
    true_peak REAL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


@dataclass
class GenerationRecord:
    id: int
    project_name: str
    project_path: str
    output_path: str
    duration_seconds: float
    word_count: int
    voice_id: str
    wpm_target: int
    lufs: float
    true_peak: float
    created_at: str


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(data_dir() / DB_NAME))
    conn.row_factory = sqlite3.Row
    conn.execute(_SCHEMA)
    return conn


def record_generation(
    project_name: str, project_path: str, output_path: str,
    duration_seconds: float, word_count: int, voice_id: str,
    wpm_target: int, lufs: float, true_peak: float,
) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO generations (project_name, project_path, output_path,"
            " duration_seconds, word_count, voice_id, wpm_target, lufs,"
            " true_peak) VALUES (?,?,?,?,?,?,?,?,?)",
            (project_name, str(project_path), str(output_path),
             duration_seconds, word_count, voice_id, wpm_target, lufs,
             true_peak),
        )
        return int(cursor.lastrowid or 0)


def recent_generations(limit: int = 25) -> list[GenerationRecord]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM generations ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [GenerationRecord(**dict(row)) for row in rows]


__all__ = [
    "AutosaveManager",
    "GenerationRecord",
    "autosave_path",
    "discard_snapshot",
    "has_recovery_snapshot",
    "recover",
    "recent_generations",
    "record_generation",
]
