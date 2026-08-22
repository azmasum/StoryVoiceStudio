"""Tests for the emotion engine."""
from emotion.analyzer import analyze_sentence, annotate_script, detect_story_structure
from emotion.presets import get_preset, preset_names
from emotion.prosody import plan_prosody, wpm_to_length_scale


def test_whisper_detection():
    result = analyze_sentence('"Stay down," he whispered urgently.')
    assert result.emotion == "WHISPER"


def test_cue_emotions():
    assert analyze_sentence("She sobbed into her hands.").emotion == "SAD"
    assert analyze_sentence("He laughed at the joke.").emotion == "HAPPY"


def test_uncertain_stays_neutral():
    assert analyze_sentence("The table was made of wood.").emotion == "NEUTRAL"


def test_dialogue_detection():
    result = analyze_sentence('"Why now?" John asked quietly.')
    assert result.is_dialogue
    assert result.speaker == "John"


def test_annotate_script_inserts_tags():
    text = 'She whispered the secret. The table was wooden.'
    annotated = annotate_script(text)
    assert "[WHISPER]" in annotated


def test_story_structure():
    sentences = [
        "It began on a cold morning.",
        "The town was quiet.",
        "But everything changed that night.",
        "Nobody knew what waited below.",
        "Finally, it was over.",
        "In the end, peace returned.",
    ]
    parts = detect_story_structure(sentences)
    labels = [p.label for p in parts]
    assert labels[0] == "Introduction"
    assert len(parts) >= 2


def test_presets_exist():
    names = preset_names()
    for expected in ("HORROR", "DOCUMENTARY", "MYSTERY", "CINEMATIC"):
        assert expected in names
    horror = get_preset("HORROR")
    assert horror.wpm < 155  # slower than default
    assert horror.pause_scale > 1.0


def test_prosody_planning():
    plan = plan_prosody("FEAR", effects=frozenset({"whisper"}),
                        pause_before=0.0, pause_after=1.0,
                        global_intensity=1.0)
    assert plan.length_scale > 1.0     # fear slows speech
    assert plan.pause_after > 1.0      # pauses are stretched
    assert plan.intensity > 0


def test_wpm_scale_conversion():
    # Natural rate 175 WPM targeting 155 -> slightly slower (scale > 1).
    scale = wpm_to_length_scale(175, 155)
    assert 1.0 < scale < 1.3
