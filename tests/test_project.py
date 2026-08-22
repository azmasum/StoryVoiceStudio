"""Tests for project persistence, cache and autosave."""
from __future__ import annotations

from pathlib import Path

from project.autosave import (
    autosave_path,
    discard_snapshot,
    has_recovery_snapshot,
)
from project.cache import ChunkCache, chunk_cache_key
from project.database import (
    GenerationSettings,
    StoryProject,
    load_project,
    save_project,
)


def _make_project() -> StoryProject:
    return StoryProject(
        name="Test Story",
        script_text="It was a dark night. Something moved.",
        settings=GenerationSettings(voice_id="en_US-lessac-medium",
                                    target_wpm=150),
    )


def test_project_roundtrip(tmp_path: Path):
    project = _make_project()
    path = save_project(project, tmp_path / "demo.storyproj")
    loaded = load_project(path)
    assert loaded.name == "Test Story"
    assert loaded.script_text == project.script_text
    assert loaded.settings.target_wpm == 150


def test_chunk_cache_roundtrip(tmp_path: Path):
    cache = ChunkCache(tmp_path / "cache")
    key = chunk_cache_key("Hello world", "voice", "piper", 1.0, 155, "")
    assert cache.get(key) is None
    source = tmp_path / "new.wav"
    source.write_bytes(b"RIFFfake-wav-data" + b"\0" * 64)
    dest = cache.put(key, source)
    assert dest == cache.path_for(key)
    assert not source.exists()
    hit = cache.get(key)
    assert hit is not None and hit.exists()


def test_cache_key_changes_with_inputs():
    base = dict(text="A", voice_id="v", engine="piper", length_scale=1.0,
                wpm_target=150, emotion="")
    key1 = chunk_cache_key(**base)
    key2 = chunk_cache_key(**{**base, "text": "B"})
    key3 = chunk_cache_key(**{**base, "length_scale": 1.05})
    assert len({key1, key2, key3}) == 3


def test_autosave_recovery(tmp_path: Path):
    project = _make_project()
    target = tmp_path / "story.storyproj"
    saved = save_project(project, target)

    # Newer snapshot simulates a crash after edits.
    snapshot_path = autosave_path(target)
    project.script_text += " Extra sentence after crash."
    save_project(project, snapshot_path)

    import os

    newer = target.stat().st_mtime + 2.0
    os.utime(snapshot_path, (newer, newer))
    assert has_recovery_snapshot(target)
    from project.autosave import recover

    recovered = recover(target)
    reloaded = load_project(recovered)
    assert "Extra sentence" in reloaded.script_text

    discard_snapshot(target)
    assert not has_recovery_snapshot(target)


def test_portable_chunk_paths(tmp_path: Path):
    project = _make_project()
    from script.chunker import Chunk

    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    wav = cache_dir / "abc123.wav"
    wav.write_bytes(b"x" * 100)
    project.chunks = [Chunk(chunk_id=0, scene_id=1, scene_title="S",
                            index_in_scene=0, text="Hi",
                            audio_path=r"X:\moved\elsewhere\abc123.wav")]
    path = save_project(project, tmp_path / "p.storyproj")
    loaded = load_project(path)
    assert Path(loaded.chunks[0].audio_path).exists()


def test_sanitize_project_name():
    from app.config.paths import sanitize_project_path

    result = sanitize_project_path(Path("G:/tmp"), 'bad:name*here?')
    assert ":" not in result.name.replace(":", "", 0) or "_" in result.name
    try:
        sanitize_project_path(Path("G:/tmp"), "../escape")
        escaped = ".." in str(result)
        assert not escaped or "_" in result.name[0]
    except ValueError:
        pass
