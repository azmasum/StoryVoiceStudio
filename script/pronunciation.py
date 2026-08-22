"""Custom pronunciation dictionary support.

Entries map written forms to phonetic respellings, e.g.:

    {"Worcestershire": "WOOS-ter-sheer"}

The dictionary is applied AFTER numeric normalization so entries can safely
contain digits. Matching is case-sensitive for capitalized words (proper
nouns) and case-insensitive otherwise.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.config.paths import repo_asset_dir

BUILTIN_PRONUNCIATIONS = {
    "Worcestershire": "WOOS-ter-sheer",
    "Gloucester": "GLOS-ter",
    "Leicester": "LES-ter",
    "Arkansas": "AR-kan-saw",
    "Illinois": "il-i-NOY",
    "Nevada": "nuh-VAD-uh",
    "Oregon": "OR-uh-gun",
    "Detroit": "dih-TROIT",
    "Chicago": "shih-KAW-go",
    "Louisville": "LOO-uh-vul",
}


def builtin_dictionary_path() -> Path:
    return repo_asset_dir("pronunciations.json")


def load_pronunciations(extra_path: str | Path | None = None) -> dict[str, str]:
    table = dict(BUILTIN_PRONUNCIATIONS)
    path: Path | None = None
    if extra_path:
        path = Path(extra_path)
    elif builtin_dictionary_path().exists():
        path = builtin_dictionary_path()
    if path is not None:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            if isinstance(data, dict):
                table.update({str(k): str(v) for k, v in data.items()})
        except Exception:  # noqa: BLE001 - bad dictionary must not break TTS
            pass
    return table


def apply_pronunciations(text: str, dictionary: dict[str, str]) -> tuple[str, int]:
    """Replace dictionary keys in *text*.

    Returns the new text and the number of substitutions made. Longer keys
    are replaced first so multi-word phrases win over substrings.
    """
    replacements = 0
    for original in sorted(dictionary, key=len, reverse=True):
        spoken = dictionary[original]
        if not original or not spoken or original == spoken:
            continue
        if original[:1].isupper():
            pattern = re.compile(r"\b" + re.escape(original) + r"\b")
            text, count = pattern.subn(spoken.replace(" ", ","), text)
        else:
            pattern = re.compile(
                r"\b" + re.escape(original) + r"\b", re.IGNORECASE
            )
            text, count = pattern.subn(spoken.replace(" ", ","), text)
        replacements += count
    return text, replacements
