"""Tests for bundled-voice seeding (models/bundled.py)."""
from __future__ import annotations

import json

import models.bundled as bundled
from models.bundled import seed_bundled_voices


def _make_bundled(root, voice_id: str, payload: bytes = b"ONNXDATA") -> None:
    folder = root / voice_id
    folder.mkdir(parents=True)
    (folder / f"{voice_id}.onnx").write_bytes(payload)
    (folder / f"{voice_id}.onnx.json").write_text("{}", encoding="utf-8")


def test_seed_copies_missing_voices(tmp_path, monkeypatch):
    bundle = tmp_path / "bundle" / "voices"
    _make_bundled(bundle, "en_US-test-medium")
    _make_bundled(bundle, "bn_BD-test-medium")
    dest = tmp_path / "data" / "voices"
    dest.mkdir(parents=True)

    monkeypatch.setattr(bundled, "bundled_voices_dir", lambda: bundle)
    monkeypatch.setattr(bundled, "voices_dir", lambda: dest)
    monkeypatch.setattr(bundled, "installed_manifest", lambda: {})
    written = {}
    monkeypatch.setattr(bundled, "_write_manifest",
                        lambda m: written.update(m))

    seeded = seed_bundled_voices()
    assert sorted(seeded) == ["bn_BD-test-medium", "en_US-test-medium"]
    onnx = dest / "en_US-test-medium" / "en_US-test-medium.onnx"
    assert onnx.read_bytes() == b"ONNXDATA"
    assert "en_US-test-medium" in written
    assert written["en_US-test-medium"]["source"] == "bundled"


def test_seed_skips_already_installed(tmp_path, monkeypatch):
    bundle = tmp_path / "bundle" / "voices"
    _make_bundled(bundle, "en_US-test-medium")
    dest = tmp_path / "data" / "voices"
    _make_bundled(dest, "en_US-test-medium")  # already present locally

    monkeypatch.setattr(bundled, "bundled_voices_dir", lambda: bundle)
    monkeypatch.setattr(bundled, "voices_dir", lambda: dest)
    monkeypatch.setattr(bundled, "installed_manifest", lambda: {})

    assert seed_bundled_voices() == []


def test_seed_ignores_incomplete_bundle_entries(tmp_path, monkeypatch):
    bundle = tmp_path / "bundle" / "voices"
    folder = bundle / "en_US-broken-medium"
    folder.mkdir(parents=True)
    (folder / "en_US-broken-medium.onnx").write_bytes(b"x")  # no .json
    dest = tmp_path / "data" / "voices"
    dest.mkdir(parents=True)

    monkeypatch.setattr(bundled, "bundled_voices_dir", lambda: bundle)
    monkeypatch.setattr(bundled, "voices_dir", lambda: dest)
    monkeypatch.setattr(bundled, "installed_manifest", lambda: {})

    assert seed_bundled_voices() == []
    assert not (dest / "en_US-broken-medium").exists()
