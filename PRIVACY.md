# Privacy Policy

StoryVoice Studio sends narration requests to speech services — that
is how voices are produced. Everything else stays on your computer.

## What stays on your computer
- Your projects (scripts, settings, cached audio, exports)
- API keys (local settings file only)
- Application logs

## Network access — only these, only when you trigger it:
| Action | Destination | Data sent |
|--------|-------------|-----------|
| Narration via EdgeTTS (free engine) | Microsoft Edge TTS service | Script text + voice/rate/pitch config |
| Narration via Gemini (premium) | generativelanguage.googleapis.com | Script text + voice/style config; API key in header |
| Update check (manual) | api.github.com | HTTP GET for release metadata |

No analytics. No crash reporting service. No telemetry. No accounts
besides your own optional Google AI Studio key.

## Third-party services
Narration is governed by Microsoft's terms (EdgeTTS) or Google's Gemini
API Terms of Service and Privacy Policy (Gemini). Generated Gemini audio
carries a SynthID watermark applied by Google.

## Logs
Log files are written locally to help you debug issues. They never contain
your API key. Script text may appear in debug logs — redact before sharing.
You can delete logs at any time from Settings → Open Logs Folder.

## Changes
Material changes to this policy will be noted in CHANGELOG.md and releases.
