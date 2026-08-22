# Developer Guide

## Architecture

```
USER → StoryVoice Studio (PySide6)
         ↓
   app/core/generator.py        # orchestration pipeline
         ↓
   script/                      # markup, normalize, pronounce, chunk
         ↓
   emotion/                     # analyzer, presets, prosody planning
         ↓
   tts/                         # provider abstraction + Piper provider
         ↓
   audio/                       # DSP, mixing, mastering, analysis
         ↓
   music/  sfx/  timeline/      # ducking, events, transitions
         ↓
   project/  export/            # .storyproj, cache, autosave; WAV/FLAC/MP3
```

### Key invariants

1. **Never run TTS on the UI thread** — `app/workers/generation_worker.py`
   wraps the pipeline in a QThread.
2. **Chunk cache is content-addressed**
   (`project/cache.py:chunk_cache_key`) — changing one sentence regenerates
   only that chunk and enables resume.
3. **Music ducking is mandatory** whenever a music track is present.
4. **Quality gate before export** — `audio/analysis/quality.py`; critical
   issues raise `UserFacingError` and block deliverables.
5. **No fake functionality.** Optional future features get clean interfaces
   (`TTSProvider.supports_*`, timeline events) and honest documentation.

## Environment

Python 3.10+, Windows 10/11.

```bat
run_dev.bat            :: installs into .pylibs\ and launches the GUI
python -m pytest tests :: full test suite
```

If you prefer a classic venv:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

> Note: some Python 3.10.0 installations fail to spawn venv interpreters from
> a different drive ("Unable to create process"). The `.pylibs` layout used by
> run_dev.bat avoids that entirely.

## Code conventions

- Type hints everywhere; docstrings on public APIs.
- No giant files — one responsibility per module.
- Errors users might see must be `UserFacingError(what, why, actions)`;
  log raw tracebacks via `report_exception`.
- No global mutable state; providers are accessed through
  `tts/manager.py:get_provider`.

## Adding a TTS engine

1. Subclass `tts/base.py:TTSProvider`.
2. Register it in `tts/manager.py:available_engines/get_provider`.
3. Add model metadata to `models/registry.json` **with real license facts**
   (never fabricated) and download URLs pointing to official sources only.
4. Extend `tests/test_tts.py` with provider contract tests.
5. Emotion support: map `ProsodyPlan` fields onto your engine's controls;
   report capabilities honestly via `get_capabilities()`.

## Release flow

Tags `v*` trigger `.github/workflows/release.yml`: tests → PyInstaller build
→ portable ZIP → SHA256SUMS.txt → GitHub Release with notes.

Version lives in `app/version.py`; keep CHANGELOG.md updated.
