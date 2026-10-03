# Troubleshooting

## "A Gemini API key is required" / request rejected (400/401/403)
1. Create a key at <https://aistudio.google.com/apikey> and paste it into
   the Voice panel's **API key** field (or set the `GEMINI_API_KEY`
   environment variable for the CLI).
2. New keys can take a minute to activate - wait and retry.
3. The key must have access to the selected model
   (`gemini-2.5-pro-preview-tts` or `gemini-2.5-flash-preview-tts`).

## Quota exhausted (429)
The free tier has strict rate limits. Wait a minute and retry (the app
retries automatically 3 times), generate in smaller batches, or enable
billing in AI Studio for higher limits. Cached chunks are never billed
twice - resume and only new sentences cost API calls.

## "Gemini returned no audio"
Retry once. If the text was blocked by safety filters, rephrase it
(us-versus-them framing, graphic content and similar can be refused).

## MP3 export fails
MP3 encoding requires FFmpeg:
1. Download FFmpeg from ffmpeg.org (or winget install Gyan.FFmpeg)
2. Add its `bin` folder to PATH, or set environment variable
   `STORYVOICE_FFMPEG=C:\path\to\ffmpeg.exe`
WAV and FLAC export work without FFmpeg.

## Generation is slow
Each chunk is one API round-trip (typically a few seconds). A 10-minute
story takes a few minutes. Retries are cheap - every finished chunk is
cached, so re-runs only bill new sentences.

## The GUI does not open
Run from a terminal to see the error:
```bat
python -m app.main
```
Common causes: missing PySide6 (`pip install -r requirements.txt`), or a
corrupt settings file — delete `%LOCALAPPDATA%\StoryVoiceStudio\settings.json`
(or `userdata\settings.json` when run from source) to reset.

## Audio sounds too quiet / too loud
Check the mastering preset (YouTube = -14 LUFS). If you add very loud music,
lower the music level slider. The quality gate warns beyond ±3 LU of target.

## Resume didn't skip my finished chunks
Resume reuses chunks whose cache files still exist in the project's `cache\`
folder. Don't delete the project folder between attempts. Changing the
voice, model, emotion or style re-bills those chunks (new cache keys).

## Where are my files?
- Projects: `<userdata>\Projects\<name>\`
- Exports: inside the project folder under `exports\`
- Logs: `<userdata>\logs\` (open via Settings → Open Logs Folder)

`<userdata>` is `G:\...\StoryVoiceStudio\userdata` when run from source, or
`%LOCALAPPDATA%\StoryVoiceStudio` for installed builds. Set
`STORYVOICE_DATA_DIR` to relocate it entirely.

## Still stuck?
Search existing issues, then open a Bug Report using the issue template with
your log files attached.
