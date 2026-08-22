"""Multi-track mixdown: voice, music, SFX and ambience onto a timeline."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import soundfile as sf

from audio.analysis.resample import resample_to
from audio.dsp.filters import envelope_follow
from music.ducking import duck_music

log = logging.getLogger("audio")


@dataclass
class TrackEvent:
    """A clip placed on the timeline (audio file + position)."""

    path: str
    start_seconds: float
    gain_db: float = 0.0
    fade_in_seconds: float = 0.0
    fade_out_seconds: float = 0.0
    track: str = "VOICE"       # VOICE | MUSIC | SFX | AMBIENCE

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "start_seconds": round(self.start_seconds, 4),
            "gain_db": self.gain_db,
            "fade_in_seconds": self.fade_in_seconds,
            "fade_out_seconds": self.fade_out_seconds,
            "track": self.track,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TrackEvent":
        return cls(
            path=data["path"],
            start_seconds=float(data.get("start_seconds", 0.0)),
            gain_db=float(data.get("gain_db", 0.0)),
            fade_in_seconds=float(data.get("fade_in_seconds", 0.0)),
            fade_out_seconds=float(data.get("fade_out_seconds", 0.0)),
            track=data.get("track", "VOICE"),
        )


@dataclass
class MixResult:
    final: np.ndarray
    stems: dict[str, np.ndarray] = field(default_factory=dict)
    sample_rate: int = 44100


def _load_track_audio(path: str | Path, target_rate: int) -> np.ndarray:
    data, rate = sf.read(str(path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if rate != target_rate:
        mono = resample_to(mono, rate, target_rate)
    return mono.astype(np.float32)


def _apply_gain(samples: np.ndarray, gain_db: float) -> np.ndarray:
    if abs(gain_db) < 0.01:
        return samples
    return (samples * float(10 ** (gain_db / 20.0))).astype(np.float32)


def _fades(samples: np.ndarray, rate: int,
           fade_in: float, fade_out: float) -> np.ndarray:
    out = samples
    if fade_in > 0:
        n = min(len(out), int(rate * fade_in))
        out[:n] *= np.linspace(0.0, 1.0, n, dtype=np.float32)
    if fade_out > 0:
        n = min(len(out), int(rate * fade_out))
        out[-n:] *= np.linspace(1.0, 0.0, n, dtype=np.float32)
    return out


def render_track(events: list[TrackEvent], total_samples: int,
                 sample_rate: int) -> np.ndarray:
    """Render one track by placing every event on the shared timeline."""
    canvas = np.zeros(total_samples, dtype=np.float32)
    for event in sorted(events, key=lambda e: e.start_seconds):
        try:
            audio = _load_track_audio(event.path, sample_rate)
        except Exception:  # noqa: BLE001 - one bad asset must not kill a mix
            log.exception("Failed to load %s - skipping event", event.path)
            continue
        audio = _apply_gain(audio, event.gain_db)
        audio = _fades(audio, sample_rate, event.fade_in_seconds,
                       event.fade_out_seconds)
        start = int(event.start_seconds * sample_rate)
        end = min(len(canvas), start + len(audio))
        if end <= start or start >= len(canvas):
            continue
        canvas[start:end] += audio[:end - start]
    return canvas


def mixdown(
    voice_events: list[TrackEvent],
    music_events: list[TrackEvent],
    sfx_events: list[TrackEvent],
    ambience_events: list[TrackEvent],
    total_seconds: float | None = None,
    sample_rate: int = 44100,
    ducking_depth_db: float = 9.0,
    ducking_attack_ms: float = 200.0,
    ducking_release_ms: float = 300.0,
    return_stems: bool = False,
) -> MixResult:
    """Mix all tracks with mandatory music ducking under the voice."""
    events_by_track = {
        "VOICE": voice_events,
        "MUSIC": music_events,
        "SFX": sfx_events,
        "AMBIENCE": ambience_events,
    }
    max_end = 0.0
    for events in events_by_track.values():
        for event in events:
            max_end = max(max_end, event.start_seconds + 5.0)
    if total_seconds is not None:
        max_end = max(max_end, total_seconds)
    total_samples = max(1, int((max_end + 0.75) * sample_rate))

    stems: dict[str, np.ndarray] = {}
    for name, events in events_by_track.items():
        stems[name] = render_track(events, total_samples, sample_rate)

    # Duck MUSIC (and AMBIENCE lightly) against the VOICE stem.
    voice_stem = stems["VOICE"]
    if ducking_depth_db > 0 and float(np.max(np.abs(voice_stem))) > 1e-6:
        if float(np.max(stems["MUSIC"])) > 1e-6:
            stems["MUSIC"] = duck_music(
                stems["MUSIC"], voice_stem, sample_rate,
                depth_db=ducking_depth_db,
                attack_ms=ducking_attack_ms,
                release_ms=ducking_release_ms,
            )
        if float(np.max(stems["AMBIENCE"])) > 1e-6:
            stems["AMBIENCE"] = duck_music(
                stems["AMBIENCE"], voice_stem, sample_rate,
                depth_db=max(3.0, ducking_depth_db / 3.0),
                attack_ms=ducking_attack_ms,
                release_ms=ducking_release_ms,
            )

    final = (
        stems["VOICE"] + stems["MUSIC"] + stems["SFX"] + stems["AMBIENCE"]
    ).astype(np.float32)

    peak = float(np.max(np.abs(final)))
    if peak > 1.0:
        final /= peak

    result = MixResult(final=final, sample_rate=sample_rate)
    if return_stems:
        result.stems = stems
    else:
        result.stems = {}
    _ = envelope_follow  # keep import surface stable for tests
    log.info("Mixdown complete: %.1fs at %d Hz", len(final) / sample_rate,
             sample_rate)
    return result


def trim_silence_tail(samples: np.ndarray, sample_rate: int,
                      threshold_db: float = -55.0) -> np.ndarray:
    """Trim trailing near-silence beyond 1 second of quiet."""
    threshold = 10 ** (threshold_db / 20.0)
    quiet = np.abs(samples) < threshold
    if not quiet.any() or quiet.all():
        return samples
    last_loud = len(samples) - int(np.argmax(quiet[::-1] == False))  # noqa: E712
    keep = min(len(samples), last_loud + sample_rate)
    return samples[:keep]
