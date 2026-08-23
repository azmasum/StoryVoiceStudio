"""Project persistence: the .storyproj format (JSON with asset references).

Large audio is never embedded - chunks reference WAV files inside the
project's ``cache/`` directory by relative path.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

from audio.mixer.mixdown import TrackEvent
from script.chunker import Chunk

log = logging.getLogger("app")

FORMAT_VERSION = 1


@dataclass
class GenerationSettings:
    voice_id: str = "en_US-lessac-medium"
    speaker_id: int | None = None
    tts_engine: str = "piper"
    target_wpm: int = 155
    preset: str = "DOCUMENTARY"
    auto_emotion: bool = True
    emotion_intensity: float = 0.7
    voice_lock: bool = True
    words_per_chunk: int = 45

    # Music / mix
    music_enabled: bool = False
    music_path: str = ""
    music_gain_db: float = -18.0
    music_category: str = "Cinematic"
    ducking_db: float = 9.0
    ducking_attack_ms: int = 200
    ducking_release_ms: int = 300

    # Mastering / export
    loudness_preset: str = "YouTube"
    custom_lufs: float | None = None
    export_format: str = "wav"
    export_stems: bool = False

    # Voice character presets
    meditation_preset: bool = False


@dataclass
class StoryProject:
    name: str = "Untitled Story"
    script_text: str = ""
    settings: GenerationSettings = field(default_factory=GenerationSettings)
    chunks: list[Chunk] = field(default_factory=list)
    timeline_events: list[TrackEvent] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    app_version: str = ""
    last_render_path: str = ""
    last_generation_stats: dict = field(default_factory=dict)

    # -- serialization --------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "format_version": FORMAT_VERSION,
            "name": self.name,
            "script_text": self.script_text,
            "settings": asdict(self.settings),
            "chunks": [c.to_dict() for c in self.chunks],
            "timeline_events": [e.to_dict() for e in self.timeline_events],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "app_version": self.app_version,
            "last_render_path": self.last_render_path,
            "last_generation_stats": self.last_generation_stats,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StoryProject":
        if int(data.get("format_version", 0)) > FORMAT_VERSION:
            log.warning("Project was saved by a newer version - loading best-effort")
        settings = GenerationSettings(**data.get("settings", {}))
        return cls(
            name=data.get("name", "Untitled Story"),
            script_text=data.get("script_text", ""),
            settings=settings,
            chunks=[Chunk.from_dict(c) for c in data.get("chunks", [])],
            timeline_events=[
                TrackEvent.from_dict(e) for e in data.get("timeline_events", [])
            ],
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            app_version=data.get("app_version", ""),
            last_render_path=data.get("last_render_path", ""),
            last_generation_stats=data.get("last_generation_stats", {}),
        )


def save_project(project: StoryProject, path: str | Path) -> Path:
    path = Path(path)
    if path.suffix != ".storyproj":
        path = path.with_suffix(".storyproj")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".storyproj.tmp")
    tmp.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")
    tmp.replace(path)
    return path


def load_project(path: str | Path) -> StoryProject:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    project = StoryProject.from_dict(data)
    _relocate_chunk_paths(project, path.parent)
    return project


def _relocate_chunk_paths(project: StoryProject, project_dir: Path) -> None:
    """Make cached chunk paths portable when a project moved on disk."""
    cache_root = project_dir / "cache"
    if not cache_root.exists():
        return
    for chunk in project.chunks:
        if not chunk.audio_path:
            continue
        candidate = cache_root / Path(chunk.audio_path).name
        if candidate.exists():
            chunk.audio_path = str(candidate)
