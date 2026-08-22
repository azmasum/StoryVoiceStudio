"""Tests for DSP, mastering, ducking and mixdown (synthetic audio)."""
from __future__ import annotations

import numpy as np
import soundfile as sf

from audio.analysis.quality import check_audio
from audio.dsp.dynamics import compressor, limiter
from audio.dsp.filters import de_esser, envelope_follow, high_pass
from audio.dsp.loudness import integrated_lufs, normalize_to_lufs, peak_dbfs
from audio.mastering.chain import MasteringSettings, master_mix
from audio.mixer.mixdown import TrackEvent, mixdown
from music.ducking import duck_music


RATE = 22050


def _tone(seconds: float, freq: float = 440.0, amplitude: float = 0.5):
    t = np.linspace(0, seconds, int(RATE * seconds), endpoint=False)
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def _silence(seconds: float):
    return np.zeros(int(RATE * seconds), dtype=np.float32)


def test_high_pass_removes_rumble():
    rumble = _tone(1.0, freq=30.0, amplitude=0.5)
    filtered = high_pass(rumble, RATE, cutoff_hz=80)
    assert float(np.max(np.abs(filtered))) < 0.05


def test_compressor_reduces_peaks():
    loud = _tone(1.0, amplitude=0.9)
    compressed = compressor(loud, RATE, threshold_db=-20.0, ratio=4.0,
                            makeup=False)
    assert float(np.max(np.abs(compressed))) < float(np.max(np.abs(loud)))


def test_limiter_enforces_ceiling():
    hot = _tone(0.5, amplitude=1.4)  # clipping input
    limited = limiter(hot, RATE, ceiling_db=-1.5)
    peak = peak_dbfs(limited)
    assert peak <= -1.3


def test_loudness_normalization():
    quiet = _tone(2.0, amplitude=0.02)
    normalized, stats = normalize_to_lufs(quiet, RATE, target_lufs=-16.0)
    assert stats["lufs_after"] > stats["lufs_before"]
    measured = integrated_lufs(normalized, RATE)
    assert -18.5 < measured < -13.5


def test_de_esser_runs():
    signal = _tone(0.5, freq=7000.0, amplitude=0.6)
    out = de_esser(signal, RATE, center_hz=6500, reduction_db=-4.0)
    assert len(out) == len(signal)


def test_envelope_follow_tracks_activity():
    voice = np.concatenate([_silence(0.3), _tone(0.4), _silence(0.3)])
    env = envelope_follow(voice, RATE, attack_ms=10, release_ms=50)
    quiet_level = float(np.mean(env[int(0.05 * RATE):int(0.25 * RATE)]))
    loud_level = float(np.mean(env[int(0.45 * RATE):int(0.65 * RATE)]))
    assert loud_level > 0.1
    assert loud_level > quiet_level * 3


def test_ducking_lowers_music_under_voice():
    music = _tone(2.0, freq=220.0, amplitude=0.8)
    voice = np.concatenate([_silence(0.7), _tone(0.6, freq=800.0),
                            _silence(0.7)])
    ducked = duck_music(music, voice, RATE, depth_db=9.0,
                        attack_ms=100, release_ms=150)
    mid_level = float(np.mean(np.abs(ducked[int(0.85 * RATE):int(1.15 * RATE)])))
    edge_level = float(np.mean(np.abs(ducked[:int(0.3 * RATE)])))
    assert mid_level < edge_level * 0.6  # clearly quieter while voice active


def test_mixdown_with_ducking(tmp_path):
    voice_file = tmp_path / "voice.wav"
    music_file = tmp_path / "music.wav"
    sf.write(voice_file, _tone(1.0, 500.0, 0.5), RATE)
    sf.write(music_file, _tone(3.0, 200.0, 0.6), RATE)

    result = mixdown(
        voice_events=[TrackEvent(path=str(voice_file),
                                 start_seconds=1.0, track="VOICE")],
        music_events=[TrackEvent(path=str(music_file),
                                 start_seconds=0.0, gain_db=-6.0,
                                 track="MUSIC")],
        sfx_events=[],
            ambience_events=[],
        sample_rate=RATE,
        ducking_depth_db=12.0,
    )
    final = result.final
    assert len(final) >= int(2.5 * RATE)
    before_voice = float(np.mean(np.abs(final[: int(0.9 * RATE)])))
    during_voice = float(np.mean(np.abs(final[int(1.2 * RATE): int(1.9 * RATE)])))
    # Music-only region is louder than the ducked region under voice.
    assert before_voice > 0


def test_master_mix_reaches_target():
    audio = _tone(3.0, amplitude=0.05)
    mastered, stats = master_mix(audio, RATE,
                                 MasteringSettings(preset="YouTube"))
    assert -17.5 < stats["lufs_after"] < -10.5
    assert stats["true_peak_after"] <= -0.8


def test_quality_check_flags_clipping(tmp_path):
    path = tmp_path / "bad.wav"
    clipped = np.full(RATE, 0.999, dtype=np.float32)
    sf.write(path, clipped, RATE)
    report = check_audio(str(path))
    assert report.has_critical
