"""Script processing package: markup, normalization, chunking, pronunciation."""
from script.chunker import Chunk, build_chunks, estimate_duration
from script.markup import ParsedScript, Segment, parse_markup, strip_markup
from script.normalizer import normalize, number_to_words
from script.parser import ProcessedScript, clean_for_tts, process_script
from script.pronunciation import apply_pronunciations, load_pronunciations

__all__ = [
    "Chunk",
    "build_chunks",
    "estimate_duration",
    "ParsedScript",
    "Segment",
    "parse_markup",
    "strip_markup",
    "normalize",
    "number_to_words",
    "ProcessedScript",
    "clean_for_tts",
    "process_script",
    "apply_pronunciations",
    "load_pronunciations",
]
