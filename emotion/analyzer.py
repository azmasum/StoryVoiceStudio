"""Rule-based emotion and dialogue analysis.

Uses punctuation, dialogue tags, cue words and story structure. When the
analysis is uncertain it stays Neutral - never over-dramatize.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from script.markup import strip_markup

EMOTIONS = [
    "CALM", "HAPPY", "SAD", "FEAR", "HORROR", "SUSPENSE", "EXCITED",
    "ANGRY", "SURPRISE", "ROMANTIC", "MYSTERIOUS", "SERIOUS", "HOPEFUL",
    "DRAMATIC", "NEUTRAL",
]

# Cue phrases -> emotion. Checked case-insensitively at sentence end.
CUE_WORDS: list[tuple[tuple[str, ...], str]] = [
    (("whispered", "whispers", "whispering"), "WHISPER"),
    (("screamed", "shrieked", "yelled"), "EXCITED"),
    (("sobbed", "crying", "wept", "tears", "cried"), "SAD"),
    (("laughed", "chuckled", "smiled", "giggled"), "HAPPY"),
    (("terrified", "dread", "horrified"), "FEAR"),
    (("blood", "corpse", "dead body", "slashed"), "HORROR"),
    (("secret", "shadow", "figure in the dark", "footsteps approached"), "SUSPENSE"),
    (("suddenly", "without warning", "out of nowhere"), "SURPRISE"),
    (("angry", "furious", "rage", "snarled"), "ANGRY"),
    (("kissed", "love", "embraced"), "ROMANTIC"),
    (("mystery", "vanished", "strange", "eerie"), "MYSTERIOUS"),
    (("hope", "believed", "dreamed"), "HOPEFUL"),
]

DIALOGUE_TAG = re.compile(
    r"\b(?P<name>[A-Z][a-z]+)\s+(?P<verb>said|asked|replied|whispered|"
    r"shouted|murmured|sobbed|laughed|growled|breathed)\b"
)
QUOTE = re.compile(r"[\"“”‘’].+?[\"“”‘’]")

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class SentenceAnalysis:
    text: str
    emotion: str = "NEUTRAL"
    is_dialogue: bool = False
    speaker: str = ""
    intensity: float = 0.0  # 0..1 confidence-weighted


def _detect_dialogue(sentence: str) -> tuple[bool, str]:
    match = DIALOGUE_TAG.search(sentence)
    if match:
        return True, match.group("name")
    if QUOTE.search(sentence):
        return True, ""
    return False, ""


def _cue_emotion(sentence_lower: str) -> tuple[str, float]:
    for cues, emotion in CUE_WORDS:
        for cue in cues:
            if cue in sentence_lower:
                return emotion, 0.75
    return "", 0.0


def _punctuation_emotion(sentence: str) -> tuple[str, float]:
    if sentence.rstrip().endswith("!"):
        if any(w in sentence.lower() for w in ("no", "stop", "run", "help")):
            return "FEAR", 0.6
        return "EXCITED", 0.5
    if sentence.rstrip().endswith("?") and re.search(r"\b(who|what|where|why|how)\b",
                                                     sentence.lower()):
        return "MYSTERIOUS", 0.4
    return "", 0.0


def analyze_sentence(sentence: str) -> SentenceAnalysis:
    is_dialogue, speaker = _detect_dialogue(sentence)
    lower = sentence.lower()
    emotion, conf = _cue_emotion(lower)
    if not emotion:
        emotion, conf = _punctuation_emotion(sentence)

    # Whisper cues override to whisper effect via analyzer annotation.
    result = SentenceAnalysis(text=sentence, emotion=emotion or "NEUTRAL",
                              is_dialogue=is_dialogue, speaker=speaker,
                              intensity=conf)
    if re.search(r"\bwhisper(ed|s)?\b", lower):
        result.emotion = "WHISPER"
        result.intensity = max(result.intensity, 0.8)
    return result


@dataclass
class StoryStructurePart:
    label: str          # Introduction | Setup | Conflict | Rising Action |
                        # Suspense | Climax | Resolution | Ending
    start_sentence: int
    end_sentence: int


STRUCTURE_CUES: dict[str, tuple[str, ...]] = {
    "Introduction": ("it was a quiet", "everything started", "in the beginning",
                     "it began on"),
    "Conflict": ("but everything changed", "until one day", "then it happened",
                 "problem was"),
    "Suspense": ("little did", "what he didn't know", "nobody knew",
                 "the sound grew closer", "silence"),
    "Climax": ("finally", "at last", "it was over", "the moment came"),
    "Resolution": ("from that day", "ever since", "years later", "in the end"),
}


def detect_story_structure(sentences: list[str]) -> list[StoryStructurePart]:
    """Coarse structure detection used for pacing/music suggestions."""
    parts: list[StoryStructurePart] = []
    n = len(sentences)
    if n == 0:
        return parts

    def find_first(cues: tuple[str, ...], start: int) -> int:
        for i in range(start, n):
            low = sentences[i].lower()
            if any(cue in low for cue in cues):
                return i
        return -1

    boundaries: list[tuple[int, str]] = [(0, "Introduction")]
    conflict = find_first(STRUCTURE_CUES["Conflict"], n // 10)
    if conflict > 0:
        boundaries.append((conflict, "Conflict"))
    suspense = find_first(STRUCTURE_CUES["Suspense"], max(conflict, n // 3))
    if suspense > max(conflict, 0):
        boundaries.append((suspense, "Suspense"))
    climax = find_first(STRUCTURE_CUES["Climax"], max(suspense, int(n * 0.7)))
    if climax > max(suspense, 0):
        boundaries.append((climax, "Climax"))
    resolution = find_first(STRUCTURE_CUES["Resolution"], max(climax, int(n * 0.85)))
    if resolution > max(climax, 0):
        boundaries.append((resolution, "Resolution"))

    for idx, (start, label) in enumerate(boundaries):
        end = boundaries[idx + 1][0] - 1 if idx + 1 < len(boundaries) else n - 1
        parts.append(StoryStructurePart(label=label, start_sentence=start,
                                        end_sentence=end))
    return parts


def annotate_script(text: str, intensity: float = 0.7) -> str:
    """Insert [EMOTION:*] / [WHISPER] markers into plain text.

    Only annotates when the rule confidence is high enough; otherwise the
    sentence keeps Neutral (no tag). *intensity* (0..1) sets the threshold
    and is applied by the prosody planner later as global strength.
    """
    sentences = SENTENCE_SPLIT_RE.split(strip_markup(text))
    threshold = 0.55 - 0.15 * min(max(intensity, 0.0), 1.0)
    out_parts: list[str] = []
    current_emotion = "NEUTRAL"
    for sentence in sentences:
        if not sentence.strip():
            continue
        analysis = analyze_sentence(sentence)
        emotion = analysis.emotion
        if emotion == "WHISPER":
            out_parts.append(f"[WHISPER]{sentence}")
            current_emotion = "NEUTRAL"
            continue
        if analysis.intensity >= threshold and emotion != current_emotion:
            out_parts.append(f"[EMOTION:{emotion}]{sentence}" if emotion != "NEUTRAL" else sentence)
            current_emotion = emotion
        else:
            out_parts.append(sentence)
    return " ".join(out_parts)


def detect_dialogues(text: str) -> list[SentenceAnalysis]:
    """Return analyses only for dialogue sentences (for character voices)."""
    return [a for a in (analyze_sentence(s) for s in SENTENCE_SPLIT_RE.split(text))
            if a.is_dialogue]
