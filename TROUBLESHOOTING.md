# Troubleshooting

## Voice download fails: "The process cannot access the file"
This is usually antivirus (Windows Defender) briefly locking the freshly
downloaded model file. The app now retries automatically — if you still see
it, wait a few seconds and press download again.

## Voice generation fails: "Voice ... is not downloaded"
Open **Models → Model Manager** and download the voice (one time, needs
internet). Everything after that runs offline.

## "The Piper TTS engine is not installed"
Run `pip install piper-tts` inside your environment, or launch through
`run_dev.bat` which installs all requirements.

## MP3 export fails
MP3 encoding requires FFmpeg:
1. Download FFmpeg from ffmpeg.org (or winget install Gyan.FFmpeg)
2. Add its `bin` folder to PATH, or set environment variable
   `STORYVOICE_FFMPEG=C:\path\to\ffmpeg.exe`
WAV and FLAC export work without FFmpeg.

## Generation is slow
- CPU mode is normal for Piper; a 10-minute story typically takes a few
  minutes on 4 cores.
- Close heavy apps; each chunk is cached, so retries are cheap.
- "Low quality" voices (`-low`) synthesize faster than `-high`.

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
folder. Don't delete the project folder between attempts.

## Where are my files?
- Projects: `<userdata>\Projects\<name>\`
- Exports: inside the project folder under `exports\`
- Voices/models: `<userdata>\models\voices\`
- Logs: `<userdata>\logs\` (open via Settings → Open Logs Folder)

`<userdata>` is `G:\...\StoryVoiceStudio\userdata` when run from source, or
`%LOCALAPPDATA%\StoryVoiceStudio` for installed builds. Set
`STORYVOICE_DATA_DIR` to relocate it entirely.

## Still stuck?
Search existing issues, then open a Bug Report using the issue template with
your log files attached.
