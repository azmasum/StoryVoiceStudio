"""Source-integrity guard: every tracked Python file must compile.

Regression test for a release once broken by a zeroed-out module
(app/ui/panels.py) that no import-based test caught: PyInstaller silently
skipped it and the frozen app crashed at startup.
"""
from __future__ import annotations

import py_compile
from pathlib import Path


def test_all_tracked_python_files_compile():
    import subprocess

    repo = Path(__file__).resolve().parents[1]
    out = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=repo, capture_output=True,
        text=True, check=True)
    files = [repo / line.strip() for line in out.stdout.splitlines()
             if line.strip()]
    assert files, "no tracked python files found"
    broken = []
    for path in files:
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError:
            broken.append(path.name)
    assert not broken, f"uncompilable modules: {broken}"


def test_no_null_bytes_in_tracked_sources():
    import subprocess

    repo = Path(__file__).resolve().parents[1]
    out = subprocess.run(
        ["git", "ls-files", "*.py"], cwd=repo, capture_output=True,
        text=True, check=True)
    corrupt = []
    for line in out.stdout.splitlines():
        if not line.strip():
            continue
        data = (repo / line.strip()).read_bytes()
        if b"\x00" in data:
            corrupt.append(line.strip())
    assert not corrupt, f"null bytes in: {corrupt}"
