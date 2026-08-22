"""Long-form script chunking.

Splits scripts hierarchically: scene markers -> paragraphs -> sentences ->
(clause fallback only when a single sentence exceeds the size limit).
Never splits inside a sentence unless absolutely necessary.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from script.markup import ParsedScript, Segment

SCENE_MARKER = re.compile(r"^\s*(?:\[\s*SCENE\s*:?\s*([^\]]*)\]\s*|#{1,3}\s*(.+))$", re.IGNORECASE)
SENTENCE_SPLIT = re.compile(
    r"(?<=[.!?])\s+(?=[\"'A-Z0-9])|(?<=[.!?])(?=\n)|(?<=[.!?][\"”’])\s+"
)
ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "inc",
    "ltd", "co", "ave", "blvd", "no", "vol", "approx", "dept",
}
MAX_SENTENCE_CHARS = 600


@dataclass
class Chunk:
    chunk_id: int
    scene_id: int
    scene_title: str
    index_in_scene: int
    text: str
    emotion: str = ""
    effects: frozenset[str] = field(default_factory=frozenset)
    pause_before: float = 0.0
    pause_after: float = 0.0
    voice: str = ""
    wpm_target: int = 155
    est_duration: float = 0.0
    audio_path: str = ""
    status: str = "pending"  # pending | done | failed

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "scene_id": self.scene_id,
            "scene_title": self.scene_title,
            "index_in_scene": self.index_in_scene,
            "text": self.text,
            "emotion": self.emotion,
            "effects": sorted(self.effects),
            "pause_before": self.pause_before,
            "pause_after": self.pause_after,
            "voice": self.voice,
            "wpm_target": self.wpm_target,
            "est_duration": round(self.est_duration, 3),
            "audio_path": self.audio_path,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Chunk":
        return cls(
            chunk_id=int(data["chunk_id"]),
            scene_id=int(data["scene_id"]),
            scene_title=data.get("scene_title", ""),
            index_in_scene=int(data.get("index_in_scene", 0)),
            text=data["text"],
            emotion=data.get("emotion", ""),
            effects=frozenset(data.get("effects", [])),
            pause_before=float(data.get("pause_before", 0.0)),
            pause_after=float(data.get("pause_after", 0.0)),
            voice=data.get("voice", ""),
            wpm_target=int(data.get("wpm_target", 155)),
            est_duration=float(data.get("est_duration", 0.0)),
            audio_path=data.get("audio_path", ""),
            status=data.get("status", "pending"),
        )


def _split_sentences(text: str) -> list[str]:
    parts = SENTENCE_SPLIT.split(text.replace("\r\n", "\n"))
    sentences: list[str] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        # Merge fragments that end in a known abbreviation.
        if sentences:
            tail_words = sentences[-1].split()[-1].rstrip('").').lower().rstrip(".")
            if tail_words in ABBREVIATIONS and not sentences[-1].endswith(("!", "?")):
                sentences[-1] += " " + part
                continue
        sentences.append(part)
    return sentences


def _hard_split(sentence: str, max_chars: int = MAX_SENTENCE_CHARS) -> list[str]:
    """Last-resort clause split for pathologically long sentences."""
    if len(sentence) <= max_chars:
        return [sentence]
    pieces: list[str] = []
    clauses = re.split(r"(?<=[,;:])\s+", sentence)
    current = ""
    for clause in clauses:
        if len(current) + len(clause) + 1 <= max_chars:
            current = f"{current} {clause}".strip()
        else:
            if current:
                pieces.append(current)
            current = clause
    if current:
        pieces.append(current)
    return pieces


def split_scenes(raw_text: str) -> list[tuple[int, str, list[str]]]:
    """Return [(scene_id, title, paragraphs)] with scene ids starting at 1.

    A scene begins at a ``[SCENE: title]`` or markdown heading line. Text
    before any marker becomes scene 1.
    """
    scenes: list[tuple[int, str, list[str]]] = []
    current_paragraphs: list[str] = []
    title = ""
    scene_open = False

    def push() -> None:
        if any(p.strip() for p in current_paragraphs):
            scenes.append((len(scenes) + 1, title or f"Scene {len(scenes) + 1}",
                           list(current_paragraphs)))
        current_paragraphs.clear()

    for block in raw_text.replace("\r\n", "\n").split("\n\n"):
        lines = block.split("\n")
        marker_match = None
        for line in lines:
            match = SCENE_MARKER.match(line.strip())
            if match:
                marker_match = match
                break
        if marker_match is not None:
            push()
            scene_open = True
            title = ((marker_match.group(1) or marker_match.group(2)) or "").strip()
            lines = [
                ln for ln in lines
                if ln.strip() and not SCENE_MARKER.match(ln.strip())
            ]
            current_paragraphs.append("\n".join(lines).strip())
        else:
            current_paragraphs.append(block.strip())
    push()

    _ = scene_open
    return scenes or [(1, "Scene 1", [raw_text.strip()])]


def build_chunks(
    parsed: ParsedScript,
    target_wpm: int = 155,
    voice: str = "",
    words_per_chunk: int = 45,
) -> list[Chunk]:
    """Build generation chunks from parsed segments.

    *words_per_chunk* groups consecutive sentences so each TTS request is
    comfortably short (roughly 15-25 seconds at narration pace).
    """
    chunks: list[Chunk] = []
    chunk_id = 0
    raw_text = "\n\n".join(seg.text for seg in parsed.segments if seg.text)
    scenes = split_scenes(raw_text)

    # Map each segment to its scene by locating segment text within scenes.
    flat_sentences: list[tuple[int, str, str, Segment]] = []
    search_from = 0
    scene_starts: list[tuple[str, int]] = []
    corpus = ""
    offsets: list[tuple[int, int]] = []  # (start, end) per scene body
    for sid, title, paragraphs in scenes:
        body = "\n\n".join(paragraphs)
        scene_starts.append((title, len(corpus)))
        offsets.append((len(corpus), len(corpus) + len(body)))
        corpus += body + "\n\n"

    for seg in parsed.segments:
        if not seg.text.strip():
            continue
        start = corpus.find(seg.text[:80].strip(), search_from)
        if start < 0:
            start = search_from
        scene_idx = 0
        for i, (s_start, s_end) in enumerate(offsets):
            if s_start <= start < s_end + 2:
                scene_idx = i
                break
        search_from = start
        sentences: list[str] = []
        for piece in seg.text.split("\n"):
            sentences.extend(_split_sentences(piece))
        for sentence in sentences:
            for part in _hard_split(sentence):
                if part.strip():
                    flat_sentences.append(
                        (scene_idx, "", part.strip(), seg)
                    )

    buffer: list[tuple[str, Segment, int]] = []
    buffer_scene = 0

    def emit() -> None:
        nonlocal buffer, chunk_id
        if not buffer:
            return
        texts = [item[0] for item in buffer]
        segments = [item[1] for item in buffer]
        last_scene = buffer[-1][2]
        emotions = [s.emotion for s in segments if s.emotion]
        effects: set[str] = set()
        for s in segments:
            effects |= set(s.effects)
        pause_before = 0.0
        if chunks:
            prev = chunks[-1]
            if prev.scene_id == scenes[last_scene][0]:
                pause_before = segments[0].pause_after * 0.5
        chunks.append(Chunk(
            chunk_id=chunk_id,
            scene_id=scenes[last_scene][0],
            scene_title=scenes[last_scene][1],
            index_in_scene=sum(1 for c in chunks if c.scene_id == scenes[last_scene][0]),
            text=" ".join(texts),
            emotion=emotions[-1] if emotions else "",
            effects=frozenset(effects),
            pause_before=pause_before,
            pause_after=segments[-1].pause_after,
            voice=voice,
            wpm_target=target_wpm,
        ))
        chunk_id += 1
        buffer = []

    for scene_idx, _title, sentence, seg in flat_sentences:
        if buffer and (scene_idx != buffer_scene or len(buffer) >= 4):
            emit()
        if sentence.count(" ") + 1 >= words_per_chunk:
            emit()
            buffer.append((sentence, seg, scene_idx))
            buffer_scene = scene_idx
            continue
        if not buffer:
            buffer_scene = scene_idx
        buffer.append((sentence, seg, scene_idx))

    emit()

    for chunk in chunks:
        words = max(1, len(chunk.text.split()))
        chunk.est_duration = estimate_duration(words, chunk.wpm_target, chunk.pause_after)
    return chunks


def estimate_duration(word_count: int, wpm: int, pauses: float = 0.0) -> float:
    """Estimated spoken seconds for *word_count* at *wpm* plus pause time."""
    base = (word_count / max(60, wpm)) * 60
    return round(base + pauses, 3)


def total_estimated_duration(chunks: Iterable[Chunk]) -> float:
    return sum(c.est_duration + c.pause_before + c.pause_after for c in chunks)
