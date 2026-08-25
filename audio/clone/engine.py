"""Optional voice-cloning engine (OpenVoice v2 tone-colour transfer).

Pipeline: Piper generates native-accent Bangla narration, then the
tone colour of a short reference clip (uploaded file or download link)
is transferred onto it.  Heavy dependencies (torch/librosa) live in an
optional "clone pack" folder and are imported lazily, so the base app
runs fine without them.
"""
from __future__ import annotations

import hashlib
import urllib.parse
import sys
import sys
import urllib.request
from pathlib import Path
from typing import Optional

from app.config.paths import clone_models_dir

_CONVERTER_SR = 22050          # OpenVoice v2 working rate
_REF_MIN_SECONDS = 2.5
_DOWNLOAD_MAX_BYTES = 80 * 1024 * 1024
_ALLOWED_SUFFIXES = {".wav", ".mp3", ".flac", ".ogg"}

_converter = None              # lazily created ToneColorConverter
_se_cache: dict[str, object] = {}
_status_hint = ""


def _clone_libs_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "clone_libs"
    return Path(__file__).resolve().parents[2] / "clone_libs"


def _vendor_dir() -> Path:
    return Path(__file__).resolve().parent


def ensure_sys_path() -> None:
    libs = str(_clone_libs_dir())
    vendor = str(_vendor_dir())   # makes `import openvoice` work in source mode
    for p in (libs, vendor):
        if p not in sys.path and Path(p).exists():
            sys.path.insert(0, p)


def checkpoint_paths() -> tuple[Path, Path]:
    d = clone_models_dir()
    return d / "checkpoint.pth", d / "config.json"


def is_ready() -> bool:
    ckpt, cfg = checkpoint_paths()
    if not (ckpt.exists() and cfg.exists()):
        return False
    try:
        import torch  # noqa: F401
        return True
    except Exception:
        return False


def status_text() -> str:
    ckpt, cfg = checkpoint_paths()
    if not (ckpt.exists() and cfg.exists()):
        return ("Clone pack missing: run install_clone_pack.py "
                "(models/openvoice).")
    try:
        ensure_sys_path()
        import torch  # noqa: F401
    except Exception:
        return ("Clone pack missing: clone_libs folder with torch+librosa "
                "required.")
    return "Voice clone ready."


def load_reference(source: str, dest_dir: Optional[Path] = None) -> Path:
    """Accept a local path or an http(s) link; return a local audio file."""
    source = source.strip().strip('"')
    if not source:
        raise ValueError("Reference voice: file or link required.")
    low = source.lower()
    if low.startswith(("http://", "https://")):
        name = Path(urllib.parse.urlparse(source).path).name or "reference.wav"
        suffix = Path(name).suffix.lower()
        if suffix not in _ALLOWED_SUFFIXES:
            raise ValueError(f"Unsupported link type '{suffix}'. "
                             f"Use one of: {', '.join(sorted(_ALLOWED_SUFFIXES))}")
        dest = (dest_dir or references_dir_fallback()) / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(source, headers={"User-Agent": "StoryVoiceStudio/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as out:
            total = 0
            while True:
                block = resp.read(1 << 20)
                if not block:
                    break
                total += len(block)
                if total > _DOWNLOAD_MAX_BYTES:
                    out.close()
                    dest.unlink(missing_ok=True)
                    raise ValueError("Downloaded reference is larger than 80 MB.")
                out.write(block)
        path = dest
    else:
        path = Path(source)
        if path.suffix.lower() not in _ALLOWED_SUFFIXES:
            raise ValueError(f"Unsupported audio type '{path.suffix}'. "
                             f"Use: {', '.join(sorted(_ALLOWED_SUFFIXES))}")
        if not path.exists():
            raise ValueError(f"Reference file not found: {path}")

    import soundfile as sf
    info = sf.info(str(path))
    if info.duration < _REF_MIN_SECONDS:
        raise ValueError("Reference clip too short - need at least "
                         f"{_REF_MIN_SECONDS:.0f} seconds of clean speech.")
    return path


def references_dir_fallback() -> Path:
    from app.config.paths import references_dir
    return references_dir()


def _get_converter():
    global _converter
    if _converter is not None:
        return _converter
    ensure_sys_path()
    import torch
    from openvoice.api import ToneColorConverter
    ckpt, cfg = checkpoint_paths()
    conv = ToneColorConverter(config_path=str(cfg), device="cpu",
                              enable_watermark=False)
    conv.load_ckpt(str(ckpt))
    conv.model.eval()
    _converter = conv
    return conv


def _se_for(path: Path) -> object:
    key = hashlib.sha256(str(path).encode() +
                         str(int(path.stat().st_mtime)).encode()).hexdigest()
    if key not in _se_cache:
        conv = _get_converter()
        _se_cache[key] = conv.extract_se([str(path)])
    return _se_cache[key]


def convert_audio(audio, sample_rate: int, reference_path: Path,
                  tau: float = 0.3):
    """Apply the reference speaker's timbre to `audio` (np float32).

    Returns (audio_at_original_rate, original_rate).
    """
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly

    reference_path = Path(reference_path)
    ref = load_reference(str(reference_path))

    tmp_in = reference_path.parent / "_clone_src_tmp.wav"
    tmp_out = reference_path.parent / "_clone_out_tmp.wav"
    sf.write(str(tmp_in), audio.astype(np.float32), sample_rate)
    try:
        conv = _get_converter()
        src_se = _se_for(tmp_in)
        tgt_se = _se_for(ref)
        conv.convert(audio_src_path=str(tmp_in), src_se=src_se,
                     tgt_se=tgt_se, output_path=str(tmp_out), tau=tau)
        cloned, conv_sr = sf.read(str(tmp_out), dtype="float32", always_2d=False)
    finally:
        tmp_in.unlink(missing_ok=True)
        tmp_out.unlink(missing_ok=True)

    if conv_sr != sample_rate:
        g = __import__("math").gcd(conv_sr, sample_rate)
        cloned = resample_poly(cloned, sample_rate // g, conv_sr // g)
    peak = float(np.max(np.abs(cloned))) if len(cloned) else 0.0
    if peak > 0.99:
        cloned *= 0.98 / peak
    return cloned.astype(np.float32), sample_rate
