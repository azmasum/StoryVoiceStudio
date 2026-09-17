"""Indic Parler-TTS provider - expressive transformer narration (optional).

ai4bharat/indic-parler-tts (Apache-2.0) speaks 21 languages including
Bengali, with emotion/style control through natural-language description
prompts. It needs torch + transformers (shipped in the clone_libs pack)
and a one-time ~4 GB model download into models/parler.

The upstream repo is access-gated: the user accepts the license on
Hugging Face once and pastes a read-only token into the Model Manager.
Without the model files every method raises a UserFacingError that says
exactly that - the base Piper path is never affected.
"""
from __future__ import annotations

import logging
import time
from pathlib import Path

from app.utils.errors import UserFacingError
from tts.base import (
    ProviderCapabilities,
    SynthesisResult,
    TTSProvider,
    VoiceInfo,
)

log = logging.getLogger("tts")

REPO_FILES = (
    "config.json",
    "generation_config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "tokenizer.model",
    "special_tokens_map.json",
    "preprocessor_config.json",
)
# Tokenizer payloads that may live in the text-encoder repo instead.
ENCODER_FILES = (
    "tokenizer_config.json",
    "tokenizer.json",
    "spiece.model",
    "sentencepiece.bpe.model",
    "tokenizer.model",
    "special_tokens_map.json",
)

_EMOTION_TONE = {
    "CALM": "calm and steady",
    "HAPPY": "cheerful and bright",
    "SAD": "sad and low",
    "FEAR": "fearful and trembling",
    "HORROR": "dark and ominous",
    "SUSPENSE": "tense and suspenseful",
    "EXCITED": "excited and energetic",
    "ANGRY": "angry and forceful",
    "SURPRISE": "surprised",
    "ROMANTIC": "warm and tender",
    "MYSTERIOUS": "mysterious and quiet",
    "SERIOUS": "serious and formal",
    "HOPEFUL": "hopeful and uplifting",
    "DRAMATIC": "dramatic and powerful",
    "WHISPER": "softly whispered",
    "NEUTRAL": "calm and steady",
}


def _clone_libs_dir() -> Path:
    import sys

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "clone_libs"
    return Path(__file__).resolve().parents[2] / "clone_libs"


def _ensure_path() -> None:
    import sys

    libs = str(_clone_libs_dir())
    if libs not in sys.path and Path(libs).exists():
        # Appended (not prepended) so the app's own numpy/scipy builds win
        # and only torch/transformers resolve from the pack.
        sys.path.append(libs)


def model_dir_for_repo(repo_id: str) -> Path:
    from app.config.paths import parler_dir

    safe = repo_id.replace("/", "__")
    return parler_dir() / safe


def description_for_voice(voice_id: str, emotion: str = "NEUTRAL",
                          length_scale: float = 1.0) -> str:
    """Build the Parler description prompt for a voice + emotion.

    Attribute-style prompts (no invented speaker names): the fixed persona
    keeps the voice consistent across chunks while the tone word carries
    the per-chunk emotion.
    """
    from tts.voices.catalog import get_voice

    info = get_voice(voice_id)
    gender = (info.gender if info else "female").split("+")[0]
    persona = "a female voice" if gender == "female" else "a male voice"
    accent = (info.accent if info else "") or ""
    language = "Bengali" if accent.lower().startswith("bn") else "English"
    tone = _EMOTION_TONE.get((emotion or "NEUTRAL").upper(), "calm and steady")
    if length_scale > 1.05:
        pace = "speaking slowly"
    elif length_scale < 0.95:
        pace = "speaking quickly"
    else:
        pace = "speaking at a moderate pace"
    return (f"{persona} narrating a {language} story in a {tone} tone, "
            f"{pace} with clear pronunciation and natural expression, "
            f"very high quality recording with no background noise.")


class ParlerTTSProvider(TTSProvider):
    name = "parler"

    def __init__(self) -> None:
        self._model = None
        self._tokenizer = None
        self._desc_tokenizer = None
        self._loaded_repo = ""
        self._sample_rate = 44100
        self._wpm_cache: dict[str, float] = {}

    # -- model lifecycle -------------------------------------------------

    def _repo_for(self, voice_id: str) -> str:
        from tts.voices.catalog import parler_repo

        repo = parler_repo(voice_id)
        if not repo:
            raise UserFacingError(
                what=f"Voice '{voice_id}' is not a Parler voice.",
                why="No transformer checkpoint is mapped to this voice id.",
                actions=["Pick a Parler voice from the Model Manager, or use "
                         "a Piper voice for instant offline synthesis."],
            )
        return repo

    def _require_files(self, repo_id: str) -> Path:
        model_dir = model_dir_for_repo(repo_id)
        missing = [f for f in ("config.json", "model.safetensors")
                   if not (model_dir / f).exists()]
        if missing:
            raise UserFacingError(
                what="The Parler voice model is not downloaded (~4 GB, once).",
                why=f"Missing under {model_dir}: {', '.join(missing)}.",
                actions=[
                    "Open Models > Model Manager and download a Parler voice.",
                    "The repo is access-gated: accept the license on "
                    "huggingface.co/ai4bharat/indic-parler-tts, create a "
                    "read-only token, and paste it into the Model Manager.",
                ],
            )
        return model_dir

    def load_model(self) -> None:
        """No global model - checkpoints load lazily per voice_id."""

    def unload_model(self) -> None:
        self._model = None
        self._tokenizer = None
        self._desc_tokenizer = None
        self._loaded_repo = ""

    def is_loaded(self) -> bool:
        return self._model is not None

    def _load_voice(self, voice_id: str):
        repo_id = self._repo_for(voice_id)
        if self._loaded_repo == repo_id and self._model is not None:
            return self._model
        model_dir = self._require_files(repo_id)
        _ensure_path()
        try:
            import torch
            from parler_tts import ParlerTTSForConditionalGeneration
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise UserFacingError(
                what="The transformer voice pack is not installed.",
                why="torch/transformers are missing from the clone_libs pack.",
                actions=[
                    "Re-run Install.bat (with the voice-clone pack), or",
                    "run packaging/install_clone_pack.py from the repo.",
                ],
            ) from exc
        t0 = time.time()
        _ = torch  # referenced for clarity; inference runs on CPU
        model = ParlerTTSForConditionalGeneration.from_pretrained(
            str(model_dir)).to("cpu")
        model.eval()
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        encoder_ref = str(getattr(model.config.text_encoder,
                                  "_name_or_path", "") or "")
        desc_dir = self._desc_dir(model_dir, encoder_ref)
        desc_tokenizer = AutoTokenizer.from_pretrained(str(desc_dir))
        self._model = model
        self._tokenizer = tokenizer
        self._desc_tokenizer = desc_tokenizer
        self._loaded_repo = repo_id
        try:
            self._sample_rate = int(
                model.config.audio_encoder.sampling_rate)
        except Exception:  # noqa: BLE001
            self._sample_rate = 44100
        log.info("Loaded Parler voice %s (%s) in %.1fs", voice_id, repo_id,
                 time.time() - t0)
        return model

    @staticmethod
    def _desc_dir(model_dir: Path, encoder_ref: str) -> Path:
        """Locate the description (T5) tokenizer.

        Usually an external repo (e.g. google/flan-t5-large) downloaded
        next to the checkpoint by install_voice; falls back to the model
        dir itself when the encoder ref points there.
        """
        if not encoder_ref or encoder_ref in {".", str(model_dir)}:
            return model_dir
        safe = encoder_ref.replace("/", "__")
        candidate = model_dir.parent / safe
        if (candidate / "tokenizer_config.json").exists():
            return candidate
        if (model_dir / "tokenizer_config.json").exists():
            return model_dir
        raise UserFacingError(
            what="The Parler description tokenizer is missing.",
            why=f"Text encoder '{encoder_ref}' has no local tokenizer.",
            actions=["Re-run the Parler voice download in the Model Manager "
                     "(it fetches the encoder tokenizer automatically)."],
        )

    # -- synthesis --------------------------------------------------------

    def synthesize(
        self,
        text: str,
        out_path: Path,
        voice_id: str,
        length_scale: float = 1.0,
        speaker_id: int | None = None,
    ) -> SynthesisResult:
        text = " ".join(text.split())
        if not text:
            raise ValueError("Cannot synthesize empty text.")
        model = self._load_voice(voice_id)
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        import torch

        description = description_for_voice(voice_id, "NEUTRAL", length_scale)
        prompt = self._tokenizer(text, return_tensors="pt")
        desc = self._desc_tokenizer(description, return_tensors="pt")
        started = time.time()
        with torch.no_grad():
            generation = model.generate(
                input_ids=desc.input_ids,
                attention_mask=desc.attention_mask,
                prompt_input_ids=prompt.input_ids,
                prompt_attention_mask=prompt.attention_mask,
            )
        audio = generation.cpu().numpy().squeeze().astype("float32")
        rate = self._sample_rate
        import soundfile as sf

        peak = float(max(1e-9, abs(audio).max())) if len(audio) else 1.0
        if peak > 1.0:
            audio = (audio / peak * 0.98).astype("float32")
        sf.write(str(out_path), audio, rate, subtype="PCM_16")

        duration = len(audio) / rate if rate else 0.0
        words = len(text.split())
        actual_wpm = (words / duration * 60.0) if duration > 0 else 0.0
        result = SynthesisResult(
            audio_path=out_path,
            duration_seconds=duration,
            sample_rate=rate,
            word_count=words,
            actual_wpm=round(actual_wpm, 2),
            length_scale_used=length_scale,
        )
        log.debug("Parler synth %d words in %.1fs (%.1f WPM)", words,
                  time.time() - started, result.actual_wpm)
        return result

    def synthesize_chunk(
        self,
        text: str,
        out_path: Path,
        voice_id: str,
        length_scale: float = 1.0,
    ) -> SynthesisResult:
        return self.synthesize(text, out_path, voice_id, length_scale)

    def synthesize_with_emotion(
        self,
        text: str,
        out_path: Path,
        voice_id: str,
        emotion: str,
        length_scale: float = 1.0,
    ) -> SynthesisResult:
        """Synthesis with an explicit emotion steering the description."""
        model = self._load_voice(voice_id)
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        import torch

        description = description_for_voice(voice_id, emotion, length_scale)
        prompt = self._tokenizer(text, return_tensors="pt")
        desc = self._desc_tokenizer(description, return_tensors="pt")
        with torch.no_grad():
            generation = model.generate(
                input_ids=desc.input_ids,
                attention_mask=desc.attention_mask,
                prompt_input_ids=prompt.input_ids,
                prompt_attention_mask=prompt.attention_mask,
            )
        import soundfile as sf

        audio = generation.cpu().numpy().squeeze().astype("float32")
        rate = self._sample_rate
        peak = float(max(1e-9, abs(audio).max())) if len(audio) else 1.0
        if peak > 1.0:
            audio = (audio / peak * 0.98).astype("float32")
        sf.write(str(out_path), audio, rate, subtype="PCM_16")
        duration = len(audio) / rate if rate else 0.0
        words = len(text.split())
        return SynthesisResult(
            audio_path=out_path,
            duration_seconds=duration,
            sample_rate=rate,
            word_count=words,
            actual_wpm=round((words / duration * 60.0) if duration else 0.0,
                             2),
            length_scale_used=length_scale,
        )

    # -- metadata ----------------------------------------------------------

    def natural_wpm(self, voice_id: str) -> float:
        if voice_id in self._wpm_cache:
            return self._wpm_cache[voice_id]
        from tts.providers.piper_provider import _calibration_text

        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calibration.wav"
            result = self.synthesize(_calibration_text(voice_id), path,
                                     voice_id, length_scale=1.0)
        wpm = max(60.0, min(300.0, result.actual_wpm))
        self._wpm_cache[voice_id] = wpm
        return wpm

    def estimate_duration(self, text: str, voice_id: str, wpm: int) -> float:
        # No synthesis for estimates (a Parler calibration costs minutes).
        words = max(1, len(text.split()))
        return round(words / max(60, wpm) * 60.0, 3)

    def list_voices(self) -> list[VoiceInfo]:
        from tts.voices.catalog import CATALOG_VOICES

        return [VoiceInfo(**{k: e[k] for k in VoiceInfo.__dataclass_fields__
                             if k in e})
                for e in CATALOG_VOICES if e.get("engine") == "parler"]

    def get_voice_info(self, voice_id: str) -> VoiceInfo | None:
        for voice in self.list_voices():
            if voice.voice_id == voice_id:
                return voice
        return None

    def supports_emotion(self) -> bool:
        return True  # via description prompts (see synthesize_with_emotion)

    def supports_voice_cloning(self) -> bool:
        return False

    def get_license(self) -> dict:
        return {
            "engine": "ai4bharat/indic-parler-tts",
            "license": "Apache-2.0",
            "source": "https://huggingface.co/ai4bharat/indic-parler-tts",
            "commercial_use": True,
        }

    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_emotion_natively=True,
            supports_voice_cloning=False,
            supports_pitch_control=False,
            multi_speaker=True,
        )
