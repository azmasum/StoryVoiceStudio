"""Generate a psychology-explainer audition sample for bn_BD speaker 0.

Approved direction: intelligent/confident Bangladeshi male narrator,
medium-low pitch (-1.5 st), near-natural pace (0.95x), very high clarity,
dry authoritative room, strategic tiered pauses, and a brief deeper +
slower delivery on the surprising-fact line.
"""
from pathlib import Path
import wave

import numpy as np
from scipy.signal import butter, fftconvolve, resample_poly, sosfilt, tf2sos

from app.config.paths import voices_dir
from tts.voices.catalog import get_voice

SPEAKER_ID = 0
BASE_PITCH = 2 ** (-1.5 / 12)     # about -1.5 semitones
DEEP_PITCH = 2 ** (-1.9 / 12)     # surprising facts go a touch deeper
SPEED_TARGET = 0.95               # near natural pace
LS_MULTIPLIER = SPEED_TARGET * BASE_PITCH   # decouple speed from pitch
LS_DEEP_EXTRA = 1.07              # slow briefly on the key insight

PEAK_LEVEL = 0.85                 # medium energy, present
WARM_F0 = 180
WARM_DB = 2.0                     # deep-warm without radio-boom
LOWPASS_HZ = 9000                 # keep clarity high
REVERB_TAIL = 0.25                # dry-ish authority
REVERB_WET = 0.05

# (text, pause_after_seconds, surprising_fact?)
LINES = [
    ("আপনি কি জানেন...", 1.4, False),
    ("মানুষ অনেক সময় নিজের সিদ্ধান্ত, নিজে নেয় না।", 1.0, True),
    ("বরং, কিছু psychological bias তাকে সিদ্ধান্ত নিতে বাধ্য করে।", 0.9, False),
    ("গবেষণা বলছে, আমাদের মস্তিষ্ক প্রায় শত রকমের ভুল প্রবণতা লুকিয়ে রাখে।", 1.1, False),
    ("তাই পরেরবার কোনো বড় সিদ্ধান্তের আগে, এক মিনিট থামুন।", 0.8, False),
    ("কারণ বোঝা, আর বোঝাপড়া হওয়া, এক জিনিস নয়।", 0.0, False),
]

OUT_DIR = Path(r"G:\StoryVoiceStudio\userdata\audition")


def load_voice():
    info = get_voice("bn_BD-google-medium")
    base = voices_dir() / "bn_BD-google-medium"
    from piper import PiperVoice

    return PiperVoice.load(str(base / (info.voice_id + ".onnx")))


def synth_line(voice, text, ls):
    tmp = OUT_DIR / "_r_seg.wav"
    from piper import SynthesisConfig

    with wave.open(str(tmp), "wb") as w:
        voice.synthesize_wav(
            text,
            w,
            syn_config=SynthesisConfig(speaker_id=SPEAKER_ID, length_scale=ls),
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


def process(y, sr, pitch_factor, final_line=False):
    y = sosfilt(butter(2, 70, "high", fs=sr, output="sos"), y)
    y = peaking(y, sr)
    y = sosfilt(butter(2, LOWPASS_HZ, "low", fs=sr, output="sos"), y)

    n = max(int(sr * REVERB_TAIL), 8)
    t = np.linspace(0, REVERB_TAIL, n)
    ir = np.random.default_rng(3).standard_normal(n) * np.exp(-6.9 * t / REVERB_TAIL)
    ir = sosfilt(butter(2, 4000, "low", fs=sr, output="sos"), ir)
    ir /= float(np.max(np.abs(ir))) or 1.0
    y = (1 - REVERB_WET) * y + REVERB_WET * fftconvolve(y, ir)[: len(y)]

    y = np.tanh(1.2 * y) / np.tanh(1.2)

    if final_line:
        fade_n = min(int(sr * 0.30), max(0, len(y) - 1))
        if fade_n:
            y[-fade_n:] *= np.linspace(1.0, 0.80, fade_n)

    y = resample_poly(y, 1000, int(round(1000 / pitch_factor)))
    peak = float(np.max(np.abs(y))) or 1.0
    return y / peak


def main():
    voice = load_voice()
    base_ls = LS_MULTIPLIER
    segments = []
    sr = None
    last_i = len(LINES) - 1
    for i, (text, gap, surprise) in enumerate(LINES):
        ls = round(base_ls * (LS_DEEP_EXTRA if surprise else 1.0), 4)
        pf = DEEP_PITCH if surprise else BASE_PITCH
        sr, y = synth_line(voice, text, ls)
        segments.append(process(y, sr, pf, final_line=(i == last_i)))
        if gap:
            segments.append(np.zeros(int(sr * gap)))

    full = np.concatenate(segments)
    full = full / (float(np.max(np.abs(full))) or 1.0) * PEAK_LEVEL
    dst = OUT_DIR / "v11_spk00_psych_explainer.wav"
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((full * 32767).astype(np.int16).tobytes())
    print("wrote %s (%.1f s)" % (dst.name, len(full) / sr))


if __name__ == "__main__":
    main()
