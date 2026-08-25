"""The generation pipeline: script -> chunks -> local TTS -> mix -> export.

Design goals (see master spec):

- Never generate a whole long story as one TTS request - chunked synthesis.
- Every chunk is cached; crashes resume from the last completed chunk.
- Changing one sentence regenerates only that chunk (content-addressed keys).
- WPM consistency: each chunk is measured and corrected when it drifts.
- Music is always ducked under the voice; final audio is loudness-normalized.
- Quality checks run before export; critical issues block the export.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from app.config.paths import exports_dir
from app.utils.errors import UserFacingError
from audio.analysis.quality import check_audio
from audio.dsp import meditation as meditation_mod
from audio.dsp import psych as psych_mod
from audio.mastering.chain import MasteringSettings, master_mix, master_voice
from audio.mixer.mixdown import TrackEvent, mixdown
from emotion.presets import StoryPreset, get_preset
from emotion.prosody import plan_prosody, wpm_to_length_scale
from export.mp3 import export_mp3
from export.wav import export_flac, export_wav
from project.cache import ChunkCache, chunk_cache_key
from project.database import GenerationSettings, save_project
from script.chunker import Chunk
from script.parser import process_script
from tts.manager import get_provider

log = logging.getLogger("render")

WPM_DEVIATION_LIMIT = 0.08   # regenerate once beyond 8% drift


@dataclass
class GenerationOptions:
    voice_id: str = "en_US-lessac-medium"
    speaker_id: int | None = None
    engine: str = "piper"
    target_wpm: int = 155
    preset_key: str = "DOCUMENTARY"
    auto_emotion: bool = True
    emotion_intensity: float = 0.7
    words_per_chunk: int = 45
    music_path: str = ""
    music_gain_db: float = -18.0
    ducking_db: float = 9.0
    ducking_attack_ms: int = 200
    ducking_release_ms: int = 300
    loudness_preset: str = "YouTube"
    custom_lufs: float | None = None
    sample_rate: int = 44100
    export_format: str = "wav"
    export_stems: bool = False
    clone_enabled: bool = False
    clone_ref_path: str = ""
    voice_character: str = "standard"   # standard|meditation|psychology
    preview_seconds: float = 0.0   # >0 builds a short preview render only

    @property
    def meditation_preset(self) -> bool:
        return self.voice_character == "meditation"

    @classmethod
    def from_settings(cls, settings: GenerationSettings) -> "GenerationOptions":
        character = getattr(settings, "voice_character", "") or (
            "meditation" if getattr(settings, "meditation_preset", False)
            else "standard")
        if character not in ("standard", "meditation", "psychology"):
            character = "standard"
        return cls(
            voice_id=settings.voice_id,
            speaker_id=settings.speaker_id,
            engine=settings.tts_engine,
            target_wpm=settings.target_wpm,
            preset_key=settings.preset,
            auto_emotion=settings.auto_emotion,
            emotion_intensity=settings.emotion_intensity,
            words_per_chunk=settings.words_per_chunk,
            music_path=settings.music_path if settings.music_enabled else "",
            music_gain_db=settings.music_gain_db,
            ducking_db=settings.ducking_db,
            ducking_attack_ms=settings.ducking_attack_ms,
            ducking_release_ms=settings.ducking_release_ms,
            loudness_preset=settings.loudness_preset,
            custom_lufs=settings.custom_lufs,
            export_format=settings.export_format,
            export_stems=settings.export_stems,
            clone_enabled=bool(getattr(settings, "clone_enabled", False)),
            clone_ref_path=str(getattr(settings, "clone_ref_path", "") or ""),
            voice_character=character,
        )


@dataclass
class ProgressState:
    phase: str = "idle"           # plan|voice|music|mix|master|export|done
    overall_percent: float = 0.0
    chunk_index: int = 0
    chunk_count: int = 0
    current_text: str = ""
    eta_seconds: float = 0.0
    message: str = ""


@dataclass
class GenerationOutcome:
    output_paths: list[Path] = field(default_factory=list)
    stem_paths: dict[str, Path] = field(default_factory=dict)
    duration_seconds: float = 0.0
    word_count: int = 0
    actual_wpm: float = 0.0
    lufs: float = 0.0
    true_peak: float = 0.0
    chunk_count_done: int = 0
    chunk_count_total: int = 0
    cache_hits: int = 0
    quality_issues: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


ProgressCallback = object  # callable(ProgressState) -> None


class CancelledError(Exception):
    pass


class GenerationPipeline:
    def __init__(
        self,
        project_name: str,
        project_dir: Path,
        options: GenerationOptions,
        progress_callback=None,
    ) -> None:
        self.project_name = project_name
        self.project_dir = Path(project_dir)
        self.options = options
        self.callback = progress_callback
        self.preset: StoryPreset = get_preset(options.preset_key)
        self.cache = ChunkCache(self.project_dir / "cache")
        self._cancel = threading.Event()
        self._pause = threading.Event()
        self._state = ProgressState()

    # -- control --------------------------------------------------------------

    def cancel(self) -> None:
        self._cancel.set()

    def pause(self) -> None:
        self._pause.set()

    def resume(self) -> None:
        self._pause.clear()

    @property
    def paused(self) -> bool:
        return self._pause.is_set()

    def _check_control(self) -> None:
        while self._pause.is_set() and not self._cancel.is_set():
            time.sleep(0.15)
        if self._cancel.is_set():
            raise CancelledError()

    def _report(self, **updates) -> None:
        for key, value in updates.items():
            setattr(self._state, key, value)
        if self.callback is not None:
            try:
                self.callback(self._state)
            except Exception:  # noqa: BLE001
                log.exception("Progress callback failed")

    # -- pipeline ---------------------------------------------------------------

    def build_plan(self, script_text: str) -> list[Chunk]:
        processed = process_script(
            script_text,
            target_wpm=self.options.target_wpm,
            voice=self.options.voice_id,
            words_per_chunk=self.options.words_per_chunk,
            auto_emotion=self.options.auto_emotion,
            emotion_intensity=self.options.emotion_intensity,
        )
        return processed.chunks

    def run(
        self,
        script_text: str,
        existing_chunks: list[Chunk] | None = None,
    ) -> GenerationOutcome:
        """Run the full generation. *existing_chunks* enables resume."""
        started = time.time()
        self._report(phase="plan", message="Analyzing script...")
        if existing_chunks:
            chunks = existing_chunks
        else:
            chunks = self.build_plan(script_text)
        total_words = sum(len(c.text.split()) for c in chunks)
        if not chunks:
            raise UserFacingError(
                what="The script contains no speakable text.",
                why="After normalization no sentences were found.",
                actions=["Add narration text to the editor and try again."],
            )
        self._state.chunk_count = len(chunks)

        provider = get_provider(self.options.engine)
        natural_rate = provider.natural_wpm(self.options.voice_id)

        done = 0
        cache_hits = 0
        voice_events: list[TrackEvent] = []
        cursor = 0.0
        speech_words = 0
        speech_seconds = 0.0
        character_gap = _character_gap(self.options.voice_character)
        prev_text = ""

        for chunk in chunks:
            self._check_control()
            if character_gap and prev_text and _ends_sentence(prev_text):
                cursor += character_gap
            if chunk.status == "done" and chunk.audio_path:
                # Resumed chunk: trust its recorded timing.
                import soundfile as sf

                info = sf.info(chunk.audio_path)
                duration = info.frames / info.samplerate
                voice_events.append(TrackEvent(
                    path=chunk.audio_path,
                    start_seconds=cursor + chunk.pause_before,
                    track="VOICE",
                ))
                cursor += chunk.pause_before + duration + chunk.pause_after
                speech_words += len(chunk.text.split())
                speech_seconds += duration
                done += 1
                prev_text = chunk.text
                continue

            self._report(
                phase="voice",
                chunk_index=chunk.chunk_id + 1,
                current_text=chunk.text[:120],
                message=f"Chunk {chunk.chunk_id + 1}/{len(chunks)} "
                        f"({chunk.scene_title})",
            )
            wav_path = self._synthesize_chunk(provider, chunk, natural_rate)
            chunk.audio_path = str(wav_path)
            chunk.status = "done"
            duration = _wav_duration(wav_path)
            voice_events.append(TrackEvent(
                path=str(wav_path),
                start_seconds=cursor + chunk.pause_before,
                track="VOICE",
            ))
            cursor += chunk.pause_before + duration + chunk.pause_after
            speech_words += len(chunk.text.split())
            speech_seconds += duration
            done += 1
            prev_text = chunk.text
            elapsed = time.time() - started
            per_chunk = elapsed / max(done, 1)
            remaining = (len(chunks) - done) * per_chunk
            self._report(
                overall_percent=round(done / len(chunks) * 90.0, 1),
                eta_seconds=remaining,
            )

        if self.options.preview_seconds > 0:
            return self._render_preview(chunks, voice_events, started)

        # Music track
        music_events: list[TrackEvent] = []
        if self.options.music_path:
            self._report(phase="music", message="Preparing background music...")
            total = cursor or 1.0
            music_events.append(TrackEvent(
                path=self.options.music_path,
                start_seconds=0.0,
                gain_db=self.options.music_gain_db + self.preset.music_gain_db / 2,
                fade_in_seconds=2.0,
                fade_out_seconds=4.0,
                track="MUSIC",
            ))
            _ = total

        # Mixdown with mandatory ducking
        self._report(phase="mix", overall_percent=92.0,
                     message="Mixing tracks with ducking...")
        mixed = mixdown(
            voice_events=voice_events,
            music_events=music_events,
            sfx_events=[],
            ambience_events=[],
            total_seconds=cursor,
            sample_rate=self.options.sample_rate,
            ducking_depth_db=self.options.ducking_db,
            ducking_attack_ms=self.options.ducking_attack_ms,
            ducking_release_ms=self.options.ducking_release_ms,
        )

        # Mastering bus
        self._report(phase="master", overall_percent=95.0,
                     message="Mastering...")
        lufs_target = self.options.custom_lufs
        if (self.options.voice_character == "meditation"
                and lufs_target is None):
            lufs_target = -21.0  # quieter master suits calm listening
        mastering = MasteringSettings(
            preset=self.options.loudness_preset,
            custom_lufs=lufs_target,
        )
        final_audio, loud_stats = master_mix(mixed.final, self.options.sample_rate,
                                             mastering)

        # Quality gate before writing deliverables
        temp_render = self.project_dir / "render" / "final_mix.wav"
        export_wav(final_audio, self.options.sample_rate, temp_render)
        missing = sum(1 for c in chunks if c.status != "done")
        report = check_audio(
            str(temp_render),
            target_lufs=mastering.target()[0],
            ceiling_dbtp=mastering.target()[1],
            missing_chunk_count=missing,
        )
        if report.has_critical:
            lines = report.summary_lines()
            raise UserFacingError(
                what="Quality check blocked the export.",
                why="; ".join(lines),
                actions=[
                    "Regenerate any failed chunks and run generation again.",
                    "If clipping persists, lower music gain or reduce "
                    "compression.",
                ],
            )

        # Optional voice-clone tone transfer (post-master, pre-export)
        if self.options.clone_enabled and self.options.clone_ref_path:
            self._report(phase="master", overall_percent=95.0,
                         message="Applying cloned voice...")
            try:
                from audio.clone.engine import convert_audio
                final_audio, self.options.sample_rate = convert_audio(
                    final_audio, self.options.sample_rate,
                    Path(self.options.clone_ref_path))
            except Exception as exc:  # noqa: BLE001 - surface to the user
                raise UserFacingError(
                    what="Voice clone failed.",
                    why=str(exc),
                    actions=[
                        "Check the reference file/link and try again.",
                        "Or untick 'Clone reference voice' to export "
                        "without cloning.",
                    ],
                ) from exc

        # Export deliverables
        self._report(phase="export", overall_percent=98.0,
                     message="Exporting...")
        stamp = time.strftime("%Y%m%d_%H%M%S")
        base_name = f"{_safe_name(self.project_name)}_{stamp}"
        out_dir = self.project_dir / "exports"
        outputs: list[Path] = []
        stems: dict[str, Path] = {}

        fmt = self.options.export_format.lower()
        dest = out_dir / f"{base_name}.{fmt}"
        if fmt == "mp3":
            outputs.append(export_mp3(final_audio, self.options.sample_rate,
                                      dest))
        elif fmt == "flac":
            outputs.append(export_flac(final_audio, self.options.sample_rate,
                                       dest))
        else:
            outputs.append(export_wav(final_audio, self.options.sample_rate,
                                      dest))

        if self.options.export_stems and mixed.stems:
            stem_map = {
                "Voice": mixed.stems.get("VOICE"),
                "Music": mixed.stems.get("MUSIC"),
                "SFX": mixed.stems.get("SFX"),
                "Ambience": mixed.stems.get("AMBIENCE"),
            }
            for stem_name, stem_data in stem_map.items():
                if stem_data is None or not np.any(stem_data):
                    continue
                stems[stem_name] = export_wav(
                    stem_data, self.options.sample_rate,
                    out_dir / f"{base_name}_{stem_name}.wav",
                )
            stems["FinalMix"] = outputs[0]

        duration = len(final_audio) / self.options.sample_rate
        # WPM measured on speech audio only (inserted pauses excluded).
        actual_wpm = (
            round(speech_words / speech_seconds * 60.0, 1)
            if speech_seconds > 0 else 0.0
        )

        outcome = GenerationOutcome(
            output_paths=[Path(p) for p in outputs],
            stem_paths={k: Path(v) for k, v in stems.items()},
            duration_seconds=round(duration, 2),
            word_count=total_words,
            actual_wpm=actual_wpm,
            lufs=loud_stats.get("lufs_after", 0.0),
            true_peak=loud_stats.get("true_peak_after", 0.0),
            chunk_count_done=done,
            chunk_count_total=len(chunks),
            cache_hits=cache_hits,
            quality_issues=report.summary_lines(),
            stats={
                **loud_stats,
                "elapsed_seconds": round(time.time() - started, 1),
            },
        )
        self._report(phase="done", overall_percent=100.0,
                     message=f"Done in {outcome.stats['elapsed_seconds']}s")
        log.info(
            "Generation finished: %d/%d chunks, %.1fs audio, %.1f LUFS",
            done, len(chunks), duration, outcome.lufs,
        )
        return outcome

    # -- helpers ----------------------------------------------------------------

    def _synthesize_chunk(self, provider, chunk: Chunk, natural_rate: float):
        """Synthesize one chunk through cache + WPM consistency control."""
        base_scale = wpm_to_length_scale(natural_rate, chunk.wpm_target)
        plan = plan_prosody(
            emotion=chunk.emotion or "NEUTRAL",
            effects=chunk.effects,
            pause_before=chunk.pause_before,
            pause_after=chunk.pause_after,
            preset=self.preset,
            global_intensity=self.options.emotion_intensity,
        )
        length_scale = round(base_scale * plan.length_scale, 5)

        meditation = self.options.meditation_preset
        psychology = self.options.voice_character == "psychology"
        if meditation:
            length_scale = round(
                length_scale * meditation_mod.LENGTH_SCALE_MULTIPLIER, 5)
        elif psychology:
            length_scale = round(
                length_scale * psych_mod.LENGTH_SCALE_MULTIPLIER, 5)

        key = chunk_cache_key(
            chunk.text, self.options.voice_id, self.options.engine,
            length_scale, chunk.wpm_target, chunk.emotion,
            speaker_id=self.options.speaker_id,
            character=self.options.voice_character,
        )
        cached = self.cache.get(key)
        if cached is not None:
            log.debug("Cache hit for chunk %d", chunk.chunk_id)
            return cached

        from script.parser import clean_for_tts

        tts_text = clean_for_tts(chunk.text)
        tmp = self.cache.path_for(key).with_suffix(".tmp.wav")
        result = provider.synthesize(tts_text, tmp, self.options.voice_id,
                                     length_scale=length_scale,
                                     speaker_id=self.options.speaker_id)

        # WPM consistency: correct once when the chunk drifts too much.
        # Skipped for voice characters: their pace is intentionally styled.
        deviation = (
            abs(result.actual_wpm - chunk.wpm_target) / chunk.wpm_target
            if result.actual_wpm > 0 else 0.0
        )
        if (not (meditation or psychology)
                and deviation > WPM_DEVIATION_LIMIT
                and result.actual_wpm > 0):
            corrected_scale = round(
                length_scale * result.actual_wpm / chunk.wpm_target, 5)
            retry = provider.synthesize(tts_text, tmp, self.options.voice_id,
                                        length_scale=corrected_scale,
                                        speaker_id=self.options.speaker_id)
            if abs(retry.actual_wpm - chunk.wpm_target) < deviation:
                result = retry

        _trim_chunk_tail(tmp)
        if meditation:
            _apply_meditation_dsp(tmp)
        elif psychology:
            _apply_psych_dsp(tmp)
        final_path = self.cache.put(key, tmp)
        return final_path

    def _render_preview(self, chunks, voice_events, started) -> GenerationOutcome:
        """Render only the first ~N seconds for quick quality checks."""
        limit = self.options.preview_seconds
        limited_events = [
            e for e in voice_events if e.start_seconds <= limit
        ]
        self._report(phase="mix", message="Rendering preview...")
        mixed = mixdown(
            voice_events=limited_events,
            music_events=[],
            sfx_events=[],
            ambience_events=[],
            total_seconds=min(limit, 60.0),
            sample_rate=self.options.sample_rate,
            ducking_depth_db=self.options.ducking_db,
        )
        mastering = MasteringSettings(preset=self.options.loudness_preset,
                                      custom_lufs=self.options.custom_lufs)
        audio, loud_stats = master_mix(mixed.final[:int(limit * self.options.sample_rate)],
                                       self.options.sample_rate, mastering)
        out_dir = self.project_dir / "render"
        preview_path = out_dir / "preview.wav"
        export_wav(audio, self.options.sample_rate, preview_path)
        outcome = GenerationOutcome(
            output_paths=[preview_path],
            duration_seconds=round(len(audio) / self.options.sample_rate, 2),
            chunk_count_done=len(limited_events),
            chunk_count_total=len(chunks),
            quality_issues=["PREVIEW ONLY - full render not performed."],
            stats={"elapsed_seconds": round(time.time() - started, 1)},
        )
        self._report(phase="done", overall_percent=100.0, message="Preview ready")
        return outcome

    def save_project_state(self, project) -> Path:
        """Persist the .storyproj next to the working directory."""
        return save_project(project, self.project_dir / f"{_safe_name(self.project_name)}.storyproj")


def _wav_duration(path: Path) -> float:
    import wave

    with wave.open(str(path), "rb") as wf:
        rate = wf.getframerate() or 1
        return wf.getnframes() / rate


def _trim_chunk_tail(path: Path, tail_keep_seconds: float = 0.6) -> None:
    """Cap trailing silence of a synthesized chunk at ~*tail_keep_seconds*.

    TTS engines often append long sentence silences; trimming keeps the
    final narration tight while preserving natural chunk boundaries.
    """
    import soundfile as sf

    try:
        data, rate = sf.read(str(path), dtype="float32")
    except Exception:  # noqa: BLE001
        return
    if data.ndim > 1:
        data = data.mean(axis=1)
    threshold = 10 ** (-50.0 / 20.0)
    loud_indices = np.flatnonzero(np.abs(data) > threshold)
    if not len(loud_indices):
        return
    keep = int(min(len(data), loud_indices[-1] + tail_keep_seconds * rate))
    if keep < len(data) - rate * 0.05:  # only rewrite when it matters
        sf.write(str(path), data[:keep].astype(np.float32), rate,
                 subtype="PCM_16")


MEDITATION_BREATH_SECONDS = 1.5
PSYCH_BEAT_SECONDS = 0.9
_SENTENCE_ENDINGS = tuple("।!?.；")


def _ends_sentence(text: str) -> bool:
    return text.rstrip().endswith(_SENTENCE_ENDINGS)


def _character_gap(character: str) -> float:
    if character == "meditation":
        return MEDITATION_BREATH_SECONDS
    if character == "psychology":
        return PSYCH_BEAT_SECONDS
    return 0.0


def _apply_meditation_dsp(path: Path) -> None:
    """Pitch-shift + v10 profile chain, in place on a cached chunk wav."""
    import soundfile as sf

    try:
        data, rate = sf.read(str(path), dtype="float32")
    except Exception:  # noqa: BLE001
        return
    if data.ndim > 1:
        data = data.mean(axis=1)
    shifted = meditation_mod.pitch_shift_slow(data.astype(np.float64))
    processed = meditation_mod.apply_meditation_profile(shifted, rate)
    sf.write(str(path), processed.astype(np.float32), rate,
             subtype="PCM_16")


def _apply_psych_dsp(path: Path) -> None:
    """-1.5 st pitch shift + v11 profile chain, in place on a chunk wav."""
    import soundfile as sf

    try:
        data, rate = sf.read(str(path), dtype="float32")
    except Exception:  # noqa: BLE001
        return
    if data.ndim > 1:
        data = data.mean(axis=1)
    shifted = psych_mod.pitch_shift_slow(data.astype(np.float64))
    processed = psych_mod.apply_psych_profile(shifted, rate)
    sf.write(str(path), processed.astype(np.float32), rate,
             subtype="PCM_16")


def _safe_name(name: str) -> str:
    bad = set('<>:"/\\|?*')
    cleaned = "".join("_" if ch in bad else ch for ch in name).strip()
    return cleaned or "StoryVoice"


def default_output_hint() -> Path:
    return exports_dir()
