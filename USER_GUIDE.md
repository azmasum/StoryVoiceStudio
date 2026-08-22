# User Guide

StoryVoice Studio turns your written stories into professional narration —
completely offline.

## 1. First launch

1. The **first-run wizard** shows your CPU/RAM/GPU and recommends a quality tier.
2. Click the voice link to download a starter voice (~20–63 MB, one time).
   Downloads come only from the official piper-voices repository, and SHA256
   checksums are recorded automatically.
3. Press OK. You can install more voices any time via **Models → Model Manager**.

## 2. Writing your script

Paste or import (File → Import Script) your story. Supported markers:

| Marker | Effect |
|--------|--------|
| `[SCENE: Title]` | Starts a new scene (also `# Title` markdown headings) |
| `[PAUSE:1.5]` | Inserts 1.5 seconds of silence |
| `[EMOTION:FEAR]` | Applies an emotion until changed (CALM, HAPPY, SAD, FEAR, HORROR, SUSPENSE, EXCITED, ANGRY, SURPRISE, ROMANTIC, MYSTERIOUS, SERIOUS, HOPEFUL, DRAMATIC) |
| `[WHISPER]` | Whispered delivery |

Without markers, **automatic emotion detection** reads dialogue tags
("she whispered"), cue words ("screamed", "sobbed") and punctuation. When in
doubt it stays Neutral — never over-dramatic.

Numbers, years, dates and currency are normalized for natural US-English
speech ($1,250 → "one thousand two hundred fifty dollars"). Add custom
pronunciations to `assets/pronunciations.json`.

## 3. Choosing sound

- **Preset**: Documentary, Horror, Mystery, True Crime, Emotional,
  Motivational, Romance, Sci-Fi, Historical, Bedtime, Dark Story, Cinematic.
  Each sets WPM, pause length, emotion intensity, music mood and mastering.
- **Voice**: 7 US-English voices (male/female). Keep **VOICE LOCK** on so all
  chunks use identical settings.
- **WPM**: target speaking rate (120–180). Each chunk is measured; drifting
  chunks are re-synthesized once to keep the narration consistent.

## 4. Music

Enable background music, pick any WAV/MP3/FLAC/OGG/M4A you legally own.
Music is automatically **ducked** under narration:

- Depth: 0–18 dB (default 9 dB)
- Attack: how fast ducking kicks in (default 200 ms)
- Release: how fast music returns (default 300 ms)

Only use music licensed for your use case — nothing copyrighted is bundled.

## 5. Generating

1. **30s Preview** renders the first half-minute for a quick check.
2. **GENERATE AUDIO** processes the whole story chunk by chunk with live
   progress and ETA. Pause/Resume/Cancel at any time.
3. If the app closes mid-generation, reopen the project and choose
   **Resume generation?** — completed chunks load from cache instantly.
4. Editing one sentence only regenerates that sentence's chunk.

## 6. Exporting

Choose WAV / MP3 / FLAC and optionally stems (Voice/Music/SFX/Ambience).
Loudness presets: YouTube (-14 LUFS), Podcast (-16), Audiobook (-18),
Cinematic (-16). A quality gate checks clipping, missing chunks, loudness and
silence before export; critical issues block the export with instructions.

MP3 export needs FFmpeg: install it and add to PATH, or set the
`STORYVOICE_FFMPEG` environment variable.

## 7. Projects

- **Save/Open** `.storyproj` files (script + settings + timeline references;
  audio lives beside them in `cache/`, never embedded).
- Autosave runs every minute (configurable); after a crash you'll be offered
  recovery from the newest snapshot.

## 8. Keyboard shortcuts

| Keys | Action |
|------|--------|
| Ctrl+N / Ctrl+O / Ctrl+S | New / Open / Save project |
| Ctrl+Shift+S | Save As |
| Ctrl+Enter | Generate audio |
| Space (in editor) | standard text editing |

## 9. Troubleshooting

See TROUBLESHOOTING.md. Logs: **Settings → Open Logs Folder**.
