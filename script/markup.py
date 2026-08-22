"""Emotion / effect markup tokenizer.

Supported inline tags (case-insensitive):

    [EMOTION:FEAR] [EMOTION:SAD] [EMOTION:EXCITED] [EMOTION:CALM] ...
    [PAUSE:1.5]            seconds
    [WHISPER] [EMPHASIS] [BREATH] [LAUGH] [CRY] [LOW] [HIGH]

Tags apply from their position until the next tag of the same family or the
end of the paragraph. Unknown tags are stripped safely and reported.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator

TAG_PATTERN = re.compile(r"\[([A-Z_a-z]+)(?::([^\]]*))?\]")

EFFECT_TAGS = {
    "WHISPER": "whisper",
    "EMPHASIS": "emphasis",
    "BREATH": "breath",
    "LAUGH": "laugh",
    "CRY": "cry",
    "LOW": "low",
    "HIGH": "high",
}


@dataclass
class Segment:
    """A run of plain text with the state active while it was spoken."""

    text: str
    emotion: str = ""
    effects: frozenset[str] = field(default_factory=frozenset)
    pause_after: float = 0.0


@dataclass
class ParsedScript:
    segments: list[Segment]
    unknown_tags: list[str] = field(default_factory=list)

    @property
    def plain_text(self) -> str:
        return "\n".join(s.text for s in self.segments if s.text.strip())

    def iter_words(self) -> int:
        return sum(len(s.text.split()) for s in self.segments)


def parse_markup(raw: str) -> ParsedScript:
    """Split *raw* into ordered segments carrying emotion/effect/pause state.

    Paragraph breaks are preserved inside segment text so the chunker can
    still reason about scene structure.
    """
    segments: list[Segment] = []
    unknown: list[str] = []
    emotion = ""
    effects: set[str] = set()
    pending_pause = 0.0

    def flush(text: str) -> None:
        nonlocal pending_pause
        if not text.strip() and pending_pause == 0.0:
            return
        if segments and not text.strip():
            segments[-1].pause_after += pending_pause
            pending_pause = 0.0
            return
        if text.strip():
            segments.append(Segment(
                text=text.rstrip(),
                emotion=emotion,
                effects=frozenset(effects),
                pause_after=pending_pause,
            ))
        else:
            segments.append(Segment(text="", pause_after=pending_pause))
        pending_pause = 0.0

    pos = 0
    buffer: list[str] = []
    for match in TAG_PATTERN.finditer(raw):
        buffer.append(raw[pos:match.start()])
        pos = match.end()
        head = match.group(1).upper()
        value = (match.group(2) or "").strip()
        if head == "PAUSE":
            try:
                seconds = max(0.0, min(10.0, float(value or "1")))
            except ValueError:
                seconds = 1.0
            flush("".join(buffer))
            buffer = [""]
            pending_pause += seconds
            continue
        if head in EFFECT_TAGS:
            flush("".join(buffer)); buffer = []
            effects.add(EFFECT_TAGS[head])
            continue
        if head == "EMOTION":
            flush("".join(buffer)); buffer = []
            emotion = value.upper() if value else ""
            continue
        unknown.append(match.group(0))

    buffer.append(raw[pos:])
    flush("".join(buffer))

    # Drop empty helper segments that carry no pauses either.
    segments = [s for s in segments if s.text.strip() or s.pause_after > 0]
    return ParsedScript(segments=segments, unknown_tags=unknown)


def strip_markup(raw: str) -> str:
    """Return readable text with all tags removed."""
    return TAG_PATTERN.sub("", raw)
