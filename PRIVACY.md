# Privacy Policy

StoryVoice Studio is built to be **private by design**.

## What stays on your computer
- Your scripts and projects
- Generated audio files
- Downloaded voice models
- Application settings and logs

None of these are uploaded anywhere by the application.

## Network access — only these, only when you trigger it:
| Action | Destination | Data sent |
|--------|-------------|-----------|
| Voice model download | huggingface.co / github.com (official piper-voices sources) | HTTP GET for model files |
| Update check (manual) | api.github.com | HTTP GET for release metadata |

No analytics. No crash reporting service. No telemetry. No accounts.

## Third-party services
If you configure external TTS providers in the future, requests go to those
providers under their own privacy policies; local providers remain fully
offline.

## Logs
Log files are written locally to help you debug issues. They contain no
script content beyond what you choose to share when filing a bug report.
You can delete them at any time from Settings → Open Logs Folder.

## Changes
Material changes to this policy will be noted in CHANGELOG.md and releases.
