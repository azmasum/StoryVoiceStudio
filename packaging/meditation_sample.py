"""Generate a meditation-style audition sample for bn_BD speaker 12.

Implements the agreed voice profile:
- Speed 0.85x total stretch
- Pitch about -1.3 semitones (decoupled from speed)
- Very low delivery energy, gentle compression + soft limiter
- Long natural pauses between guidance lines
- Close & intimate: dry-ish, warm proximity EQ, no whisper
"""
from pathlib import Path
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt, tf2sos

from app.config.paths import voices_dir
from tts.voices.catalog import get_voice

SPEAKER_ID = 12
TARGET_SPEED = 0.85          # final playback speed vs natural
PITCH_FACTOR = 2 ** (-1.3 / 12)   # ~0.909 -> about -1.3 semitones
LENGTH_SCALE = TARGET_SPEED * PITCH_FACTOR  # decouple: ls handles the rest

PEAK_LEVEL = 0.78            # strong but not loud; limiter guards peaks
WARM_F0 = 190                # proximity warmth
WARM_DB = 3.5
LOWPASS_HZ = 5200            # soft, non-bright tone
REVERB_TAIL = 0.32           # short room only; close mic feeling
REVERB_WET = 0.08

SENTENCES = [
    ("এখন ধীরে ধীরে, চোখ বন্ধ করুন।", 1.6),
    ("একটি গভীর শ্বাস নিন।", 2.2),
    ("আরও একবার, ভেতরটা সম্পূর্ণ ভরে নিন।", 1.7),
    ("এবং ধীরে ধীরে, শ্বাস ছেড়ে দিন।", 2.8),
    ("আপনি এই মুহূর্তেই নিরাপদ।", 0.0),
]

OUT_DIR = Path(r"G:\StoryVoiceStudio\userdata\audition")


def load_voice():
    info = get_voice("bn_BD-google-medium")
    base = voices_dir() / "bn_BD-google-medium"
    from piper import PiperVoice

    return PiperVoice.load(str(base / (info.voice_id + ".onnx")))


def synth_sentence(voice, text):
    tmp = OUT_DIR / "_r_seg.wav"
    from piper import SynthesisConfig

    with wave.open(str(tmp), "wb") as w:
        voice.synthesize_wav(
            text,
            w,
            syn_config=SynthesisConfig(
                speaker_id=SPEAKER_ID, length_scale=LENGTH_SCALE
            ),
        )
    with wave.open(str(tmp), "rb") as w:
        sr = w.getframerate()
        y = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    tmp.unlink()
    return sr, y.astype(np.float64) / 32768.0


def peaking(y, sr):
    w0 = 2 * np.pi * WARM_F0 / sr
    amp = 10 ** (WARM_DB / 40)
    alpha = np.sin(w0) / (2 * 0.8)
    b = np.array([1 + alpha * amp, -2 * np.cos(w0), 1 - alpha * amp])
    a = np.array([1 + alpha / amp, -2 * np.cos(w0), 1 - alpha / amp])
    return sosfilt(tf2sos(b, a), y)


def process(y, sr):
    y = sosfilt(butter(2, 60, "high", fs=sr, output="sos"), y)
    y = peaking(y, sr)
    y = sosfilt(butter(2, LOWPASS_HZ, "low", fs=sr, output="sos"), y)

    n = int(sr * REVERB_TAIL)
    t = np.linspace(0, REVERB_TAIL, n)
    rng = np.random.default_rng(11)
    ir = rng.standard_normal(n) * np.exp(-6.9 * t / REVERB_TAIL)
    ir = sosfilt(butter(2, 3500, "low", fs=sr, output="sos"), ir)
    ir /= np.max(np.abs(ir)) or 1
    y = (1 - REVERB_WET) * y + REVERB_WET * fftconvolve(y, ir)[: len(y)]

    # gentle glue compression, then soft limiter ceiling
    y = np.tanh(1.15 * y) / np.tanh(1.15)

    # falling intonation cue: soften the tail of each line
    fade_n = min(int(sr * 0.22), max(0, len(y) - 1))
    if fade_n:
        y[-fade_n:] *= np.linspace(1.0, 0.82, fade_n)
    peak = np.max(np.abs(y)) or 1.0
    return y / peak


def main():
    voice = load_voice()
    segments = []
    sr = None
    for text, gap in SENTENCES:
        sr, y = synth_sentence(voice, text)
        segments.append(process(y, sr))
        if gap:
            pre_gap = gap * PITCH_FACTOR  # header trick slows silence too
            segments.append(np.zeros(int(sr * pre_gap)))

    full = np.concatenate(segments)
    full = full / (np.max(np.abs(full)) or 1.0) * PEAK_LEVEL
    dst = OUT_DIR / "v10_spk12_meditation_final.wav"
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(int(round(sr * PITCH_FACTOR)))
        w.writeframes((full * 32767).astype(np.int16).tobytes())
    print("wrote %s (%.1f s, pitch %.2fx, speed %.2fx)"
          % (dst.name, len(full) / sr / PITCH_FACTOR, PITCH_FACTOR, TARGET_SPEED))


if __name__ == "__main__":
    main()
