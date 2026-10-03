# StoryVoice Studio

**Professional AI Storytelling Audio — Free Voices + Gemini Premium**

A free storytelling audio production studio for Windows. Paste a story,
pick a voice, and generate expressive long-form narration with automatic
emotion, background-music ducking and professional mastering. The built-in
EdgeTTS engine is **completely free with no API key**; Gemini studio voices
are an optional premium upgrade (API key, billed by Google).

![status](https://img.shields.io/badge/platform-Windows%2010%2F11-blue) ![license](https://img.shields.io/badge/code_license-MIT-green) ![tts](https://img.shields.io/badge/TTS-EdgeTTS%20(free)%20%2B%20Gemini-blue)

---

## ✨ Features

- 🔊 **Free neural voices + Gemini premium** — 8 EdgeTTS voices (free, keyless, incl. Bangladeshi Bengali) + 30 Gemini studio voices; narrator + dialogue voices, style/emotion control in 70+ languages
- 📚 **Long-form ready** — smart scene/paragraph/sentence chunking for 10–120+ minute stories
- ⏯️ **Crash-safe resume** — every chunk is cached; interrupted generations continue where they stopped (never billed twice on Gemini)
- 🎭 **Emotion engine** — rule-based detection (`whispered`, `screamed`, punctuation cues, Bengali cues too) plus inline markup like `[EMOTION:FEAR]`, `[PAUSE:2]`, `[WHISPER]`, `[EMPHASIS]...[/EMPHASIS]`
- 🗣️ **12 storytelling presets** — Documentary, Horror, Mystery, True Crime, Emotional, Motivational, Romance, Sci-Fi, Historical, Bedtime, Dark Story, Cinematic
- 🎵 **Music + mandatory ducking** — sidechain-style envelope ducking (0–18 dB, configurable attack/release)
- 🎚️ **Professional mastering** — HPF → EQ → de-esser → compression → saturation → limiter → LUFS normalization (YouTube / Podcast / Audiobook / Cinematic targets)
- 💳 **Usage tracking** — characters + audio minutes per generation (EdgeTTS: free; Gemini: billed by Google per AI Studio pricing)
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

1. Launch and press **GENERATE AUDIO** — the free EdgeTTS engine needs no
   setup. (For Gemini voices: get a key at
   [AI Studio](https://aistudio.google.com/apikey), paste it into the Voice
   panel's **API key** field, switch Engine to Gemini.)
2. Paste or import your story (TXT/MD). Use markers if you like:
   - `[SCENE: Night Street]`, `[PAUSE:2]`, `[EMOTION:FEAR]`, `[WHISPER]`, `[EMPHASIS]...[/EMPHASIS]`
3. Pick a preset (e.g. *Horror*), narrator + dialogue voices.
4. Optional: enable background music and set ducking depth.
5. Press **30s Preview** to check quality, then **GENERATE AUDIO**.
6. Export WAV/FLAC natively; MP3 works out of the box.

### CLI

```bat
storyvoice generate story.txt --voice bn-BD-NabanitaNeural --preset HORROR --format wav
storyvoice batch .\scripts\
storyvoice voices
```

## 🖥️ Hardware Requirements

| Tier | Minimum | Recommended |
|------|---------|-------------|
| CPU  | 2 cores | 4+ cores |
| RAM  | 4 GB    | 8–16 GB     |
| Disk | 300 MB free | SSD |
| GPU  | None needed | — |
| Net  | Internet for Gemini API calls | — |

## 🗣️ Voices (EdgeTTS free + Gemini premium)

**EdgeTTS — completely free, no key, nothing to download.** Bangladeshi
Bengali (Nabanita, Pradeep) + US English (Aria, Jenny, Guy, Emma, Andrew,
Michelle). Rate/pitch emotion control included.

**Gemini — 30 studio voices** (API key + Google billing). Narrator default
Charon, dialogue default Puck; language auto-detected.

Browse + audition all voices in **Voices → Browse Voices**.
See MODEL_GUIDE.md for details.

## ⚠️ Commercial Use Notice

> **Before publishing monetized content, verify that your selected AI model,
> voice, music and SFX licenses permit commercial use.**

The application's code is MIT licensed. Model/voice/music/SFX licenses are
separate — see LICENSES.md. StoryVoice Studio never bundles copyrighted
music or SFX; you import your own legally licensed audio.

## 🔐 Privacy

EdgeTTS narration sends script text to Microsoft's service; Gemini
narration sends text + key to Google. Your API key stays in local
settings. Scripts and generated audio otherwise remain on your computer.
No analytics, no hidden telemetry. See PRIVACY.md.

## 🛠️ Build from Source

```bat
build_windows.bat        :: tests → PyInstaller EXE → dist folder
```

GitHub Actions builds Windows artifacts automatically:
`.github/workflows/tests.yml`, `build-windows.yml`, `release.yml`.

## ❓ FAQ

**Does it need internet?**
Yes for narration (EdgeTTS and Gemini are cloud services). Mixing,
mastering and export run locally.

**Is it really free?**
The built-in EdgeTTS engine is completely free — no key, no billing.
Gemini voices need your own API key and are billed by Google (a typical
10-minute story costs a few cents).

**Can I use it for monetized YouTube?**
Verify terms first: EdgeTTS is an unofficial use of Microsoft's service
(check Microsoft terms), Gemini paid tier permits commercial use (verify
in your console). You are responsible for music/SFX licensing. Generated
Gemini audio carries a SynthID watermark.

**Why does MP3 export fail?**
MP3 encoding uses FFmpeg, which isn't shipped due to licensing. Install FFmpeg
or export WAV/FLAC instead.

## 🤝 Contributing

See CONTRIBUTING.md and our Code of Conduct. Bug reports and pull requests
welcome!

## 📄 License

Application code: MIT — see LICENSE. Third-party components and models have
their own licenses: see LICENSES.md and MODEL_GUIDE.md.
