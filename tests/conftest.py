"""Shared test fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / ".pylibs"))


@pytest.fixture()
def sample_script() -> str:
    return (
        "[SCENE: The Beginning]\n\n"
        "It was a quiet night in the small town. The year was 1995, and "
        "everything seemed normal.\n\n"
        "But everything changed when Dr. Harris found the letter. It said "
        "$1,250.50 was missing, and 42% of the files were gone!\n\n"
        "\"Who did this?\" she asked.\n\n"
        "Nobody answered. Somewhere far away, a door closed."
    )
