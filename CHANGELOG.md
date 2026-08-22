# Changelog

All notable changes to StoryVoice Studio are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [Semantic Versioning](https://semver.org/).

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
