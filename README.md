# StoryVoice Studio

**Professional AI Storytelling Audio — Local, Private & Free**

A free, offline-first AI storytelling audio production studio for Windows.
Paste a story, pick a US-English voice, and generate long-form narration
with automatic emotion, background-music ducking and professional mastering —
all **locally**, with no API keys, subscriptions or cloud services.

![status](https://img.shields.io/badge/platform-Windows%2010%2F11-blue) ![license](https://img.shields.io/badge/code_license-MIT-green) ![tts](https://img.shields.io/badge/TTS-Piper%20(local)-orange)

---

## ✨ Features

- 🔊 **Real local neural TTS** — Piper engine runs ONNX voices on CPU; no GPU required
- 📚 **Long-form ready** — smart scene/paragraph/sentence chunking for 10–120+ minute stories
- ⏯️ **Crash-safe resume** — every chunk is cached; interrupted generations continue where they stopped
- 🎭 **Emotion engine** — rule-based detection (`whispered`, `screamed`, punctuation cues) plus inline markup like `[EMOTION:FEAR]`, `[PAUSE:2]`, `[WHISPER]`
- 🗣️ **12 storytelling presets** — Documentary, Horror, Mystery, True Crime, Emotional, Motivational, Romance, Sci-Fi, Historical, Bedtime, Dark Story, Cinematic
- 🎵 **Music + mandatory ducking** — sidechain-style envelope ducking (0–18 dB, configurable attack/release)
- 🎚️ **Professional mastering** — HPF → EQ → de-esser → compression → saturation → limiter → LUFS normalization (YouTube / Podcast / Audiobook / Cinematic targets)
- 🌡️ **WPM control** — target 120–180 WPM with per-chunk consistency correction and voice-lock
- 🇺🇸 **US-English normalization** — numbers, years, dates, currency, percentages, measurements spoken naturally
- 📖 **Pronunciation dictionary** — ship your own `pronunciations.json` overrides
- 🧰 **Model manager** — install only what you need; licenses shown before download; SHA256 recorded & verified
- 💾 **`.storyproj` projects** — autosave, crash recovery, portable asset references
- 🖥️ **GUI + CLI** — dark PySide6 app (Simple & Advanced modes) and `storyvoice generate|batch` commands

## 📦 Installation

### Normal users (no Python needed)
Download `StoryVoiceStudio-Setup.exe` from the [Releases](../../releases) page,
install, launch, choose a voice, paste your script, press **GENERATE AUDIO**.

### Portable
Download `StoryVoiceStudio-Portable.zip`, extract anywhere, run
`StoryVoiceStudio.exe`.

### Developers

```bat
git clone <repository_url> storyvoice-studio
cd storyvoice-studio
run_dev.bat
```

`run_dev.bat` checks Python, prepares dependencies into `.pylibs\`
(no venv needed) and launches the app. Manual equivalent:

```bat
pip install -r requirements.txt
python -m app.main
```

> Requires Python 3.10+ on Windows 10/11. No NVIDIA GPU is required;
> CUDA acceleration is used automatically when available for future engines.

## 🚀 Quick Start

1. Launch the app → the first-run wizard detects your hardware and offers a starter voice (~20–63 MB, one-time download).
2. Paste or import your story (TXT/MD). Use markers if you like:
   - `[SCENE: Night Street]`, `[PAUSE:2]`, `[EMOTION:FEAR]`, `[WHISPER]`
3. Pick a preset (e.g. *Horror*), voice, WPM (default 155).
4. Optional: enable background music and set ducking depth.
5. Press **30s Preview** to check quality, then **GENERATE AUDIO**.
6. Export WAV/FLAC natively; MP3 requires FFmpeg on PATH (see TROUBLESHOOTING).

### CLI

```bat
storyvoice generate story.txt --voice en_US-danny-low --wpm 150 --emotion auto --preset HORROR --format wav
storyvoice batch .\scripts\
storyvoice download-model en_US-lessac-medium
storyvoice voices
```

## 🖥️ Hardware Requirements

| Tier | Minimum | Recommended |
|------|---------|-------------|
| CPU  | 2 cores | 4+ cores |
| RAM  | 4 GB    | 8–16 GB     |
| Disk | 500 MB free + voice size (~20–120 MB per voice) | SSD |
| GPU  | None (CPU mode default) | Any CUDA GPU for future engines |

## 🗣️ Supported Voices (US English)

All bundled voices come from the official [rhasspy/piper-voices](https://github.com/rhasspy/piper-voices) repository (**MIT license — commercial use permitted**):

| Voice | Gender | Style | Size |
|-------|--------|-------|------|
| Lessac (Medium) | Female | Warm | ~63 MB |
| Amy (Medium) | Female | Calm | ~63 MB |
| HFC Female (Medium) | Female | Documentary | ~63 MB |
| Ryan (High) | Male | Cinematic | ~118 MB |
| Joe (Medium) | Male | Deep | ~63 MB |
| Kusal (Medium) | Male | Serious | ~63 MB |
| Danny (Low) | Male | Mystery | ~20 MB |

See MODEL_GUIDE.md for details. The TTS provider system is pluggable — new
engines can be added without touching the rest of the app.

## ⚠️ Commercial Use Notice

> **Before publishing monetized content, verify that your selected AI model,
> voice, music and SFX licenses permit commercial use.**

The application's code is MIT licensed. Model/voice/music/SFX licenses are
separate — see LICENSES.md. StoryVoice Studio never bundles copyrighted
music or SFX; you import your own legally licensed audio.

## 🔐 Privacy

Your scripts and generated audio remain on your computer unless you
explicitly use an external service. No analytics, no hidden telemetry, no
cloud dependency. See PRIVACY.md.

## 🛠️ Build from Source

```bat
build_windows.bat        :: tests → PyInstaller EXE → dist folder
```

GitHub Actions builds Windows artifacts automatically:
`.github/workflows/tests.yml`, `build-windows.yml`, `release.yml`.

## ❓ FAQ

**Does it need internet?**
Only to download voice models the first time. Generation is 100% offline.

**Is there an API key or subscription?**
No. Everything runs locally and free.

**Can I use it for monetized YouTube?**
The included Piper voices are MIT licensed (commercial use allowed), but you
are responsible for the licensing of any music/SFX you add.

**Why does MP3 export fail?**
MP3 encoding uses FFmpeg, which isn't shipped due to licensing. Install FFmpeg
or export WAV/FLAC instead.

## 🤝 Contributing

See CONTRIBUTING.md and our Code of Conduct. Bug reports and pull requests
welcome!

## 📄 License

Application code: MIT — see LICENSE. Third-party components and models have
their own licenses: see LICENSES.md and MODEL_GUIDE.md.
