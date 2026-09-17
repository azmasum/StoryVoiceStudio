# Changelog

All notable changes to StoryVoice Studio are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed (voice quality)
- Bengali voices were synthesized ~2x slower than natural (slurred,
  robotic): WPM calibration now uses a Bengali passage for Bengali
  voices instead of English text (measured 300 WPM before, ~150 after).
- All voices: TTS length_scale clamped to 0.8-1.25 so pacing control can
  no longer stretch speech into metallic/slurred artifacts; the WPM
  retry correction is clamped too and its adopt/reject comparison fixed
  (absolute vs relative WPM was compared).
- Bengali paragraphs are now split into sentences at the danda (।), so
  long passages no longer render as one giant TTS request with prosody
  drift; clause fallback and emotion analysis handle । as well.
- Chunk joints no longer click/pop: voice events get 4 ms fade-in /
  8 ms fade-out raised-cosine micro-fades at mixdown.

### Added (natural delivery)
- Bengali emotion detection: cue-word lexicon (ভয়, হাসি, কান্না...),
  Bengali dialogue verbs (বলল, জিজ্ঞেস করল...), Bengali question words
  and whisper cues — Bengali narration is no longer stuck on Neutral.
- Humanized pacing: a short storytelling breath between sentences plus
  deterministic ±15% pause jitter and ±2% rate drift, so delivery never
  ticks like a metronome (stable across runs, cache-safe).
- Real emphasis: `[EMPHASIS]...[/EMPHASIS]` scopes a span (effect close
  tags now supported) that renders slightly slower and +1.5 dB hotter;
  auto-detected `[WHISPER]` spans are scoped the same way.

### Notes (Bengali voice model)
- Audited all 16 bn_BD-google-medium speakers objectively: all healthy,
  no clipping, normal dynamics — kept default speaker 0.
- No better Piper-compatible Bengali ONNX exists upstream; the "Indian"
  colour comes from the shared espeak-ng Bengali phonemizer, which code
  cannot change. License-clean upgrade path (needs a big download and is
  slow on CPU-only machines): Indic Parler-TTS (Apache-2.0, Bengali +
  emotion control) or IndicF5-Bangladeshi (Bangladeshi accent finetune).

## [0.1.0] - 2026-08-22

First public alpha.

### Added
- Local neural TTS via Piper (ONNX, CPU-first; CUDA auto-detected)
- 7 US-English voices with license/source metadata and SHA256 recording
- Script pipeline: markup parser, US-English normalization, pronunciation
  dictionary, scene/sentence chunker
- Emotion engine: rule-based analyzer, 14 emotions, 12 storytelling presets,
  prosody planning (WPM targeting with consistency correction + voice lock)
- Audio DSP: HPF, tilt EQ, static de-esser dip, compressor, saturation,
  lookahead limiter, LUFS normalization with transparent peak limiting
- Music ducking (mandatory when music present) with attack/release controls
- Mixdown with VOICE/MUSIC/SFX/AMBIENCE stems; waveform peak cache
- Quality gate before export (clipping, loudness drift, silence, missing
  chunks)
- Export WAV/FLAC natively; MP3 via user-installed FFmpeg
- `.storyproj` project format, content-addressed chunk cache (resume),
  autosave + crash recovery snapshots, SQLite generation history
- PySide6 GUI: dark theme, Simple/Advanced modes, waveform view, model
  manager with progress, first-run wizard, update checker (manual)
- CLI: `generate`, `batch`, `voices`, `models`, `download-model`, `version`
- Test suite (48 tests), GitHub Actions CI/CD workflows
