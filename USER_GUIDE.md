# User Guide

StoryVoice Studio turns your written stories into professional narration
with Google Gemini voices.

## 1. First launch

1. Get a free API key at
   [AI Studio](https://aistudio.google.com/apikey).
2. Paste it into the Voice panel's **API key** field (stored on this PC
   only, never logged).
3. Pick a narrator voice (default **Charon**) and press OK.

Usage is billed by Google per AI Studio pricing — a typical 10-minute
story costs a few cents. Every generation shows its characters + audio
minutes.

## 2. Writing your script

Paste or import (File → Import Script) your story. Supported markers:

| Marker | Effect |
|--------|--------|
| `[SCENE: Title]` | Starts a new scene (also `# Title` markdown headings) |
| `[PAUSE:1.5]` | Inserts 1.5 seconds of silence |
| `[EMOTION:FEAR]` | Applies an emotion until changed (CALM, HAPPY, SAD, FEAR, HORROR, SUSPENSE, EXCITED, ANGRY, SURPRISE, ROMANTIC, MYSTERIOUS, SERIOUS, HOPEFUL, DRAMATIC) |
| `[WHISPER]` | Whispered delivery |
| `[EMPHASIS]...[/EMPHASIS]` | Emphasized span: rendered slightly slower and hotter so it lands with weight |

Without markers, **automatic emotion detection** reads dialogue tags
("she whispered"), cue words ("screamed", "sobbed") and punctuation — in
both English and Bengali. When in
doubt it stays Neutral — never over-dramatic.

Numbers, years, dates and currency are normalized for natural US-English
speech ($1,250 → "one thousand two hundred fifty dollars"). Add custom
pronunciations to `assets/pronunciations.json`.

## 3. Choosing sound

- **Preset**: Documentary, Horror, Mystery, True Crime, Emotional,
  Motivational, Romance, Sci-Fi, Historical, Bedtime, Dark Story, Cinematic.
  Each sets WPM, pause length, emotion intensity, music mood and mastering.
- **Voice**: 30 Gemini studio voices. **Narrator** reads the story;
  **Dialogue** (default Puck) reads dialogue-heavy chunks — pick clearly
  different timbres so speakers stay distinct. Browse + audition all 30 in
  **Voices → Browse Voices**.
- **Model**: `gemini-2.5-pro-preview-tts` (best quality) or
  `gemini-2.5-flash-preview-tts` (faster/cheaper).
- **WPM**: target speaking rate estimate (120–180). Pace is steered with
  style directions since the API has no rate knob.

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
