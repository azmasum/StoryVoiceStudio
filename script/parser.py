"""Script processing pipeline: markup -> normalize -> pronounce -> chunk."""
from __future__ import annotations

from dataclasses import dataclass

from script.chunker import Chunk, build_chunks
from script.markup import ParsedScript, parse_markup, strip_markup
from script.normalizer import normalize
from script.pronunciation import apply_pronunciations, load_pronunciations


@dataclass
class ProcessedScript:
    raw_text: str
    parsed: ParsedScript
    chunks: list[Chunk]
    word_count: int
    pronunciation_hits: int = 0

    @property
    def estimated_duration(self) -> float:
        return sum(c.est_duration + c.pause_before + c.pause_after for c in self.chunks)


def process_script(
    raw_text: str,
    target_wpm: int = 155,
    voice: str = "",
    words_per_chunk: int = 45,
    pronunciation_file: str | None = None,
    auto_emotion: bool = True,
    emotion_intensity: float = 0.7,
) -> ProcessedScript:
    """Run the full text pipeline and return chunked, annotated output."""
    parsed = parse_markup(raw_text)
    plain = parsed.plain_text
    normalized = normalize(plain)
    dictionary = load_pronunciations(pronunciation_file)
    normalized, hits = apply_pronunciations(normalized, dictionary)

    if auto_emotion:
        # Imported lazily to avoid a circular dependency at module load.
        from emotion.analyzer import annotate_script

        normalized = annotate_script(normalized, intensity=emotion_intensity)

    reparsed = parse_markup(normalized)
    chunks = build_chunks(reparsed, target_wpm=target_wpm, voice=voice,
                          words_per_chunk=words_per_chunk)
    return ProcessedScript(
        raw_text=raw_text,
        parsed=reparsed,
        chunks=chunks,
        word_count=sum(len(c.text.split()) for c in chunks),
        pronunciation_hits=hits,
    )


def clean_for_tts(text: str) -> str:
    """Final text sent to the TTS engine (markup removed)."""
    return " ".join(strip_markup(text).split())


__all__ = [
    "ProcessedScript",
    "process_script",
    "clean_for_tts",
    "parse_markup",
    "strip_markup",
]
