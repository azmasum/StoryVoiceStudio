# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| latest release | ✅ |
| older releases | ❌ (please update) |

## Reporting a vulnerability

**Do not open a public issue for security problems.**

Use GitHub's "Report a vulnerability" (Security → Advisories) or contact the
maintainers directly. Include:

- Affected version / commit
- Steps to reproduce
- Impact assessment

You'll get an acknowledgment within 7 days. We aim to ship fixes for
confirmed issues within 30 days and will credit reporters in the release
notes unless anonymity is requested.

## Scope notes

StoryVoice Studio runs locally. Areas of particular interest:

- Model download integrity (checksum handling, URL validation)
- Path traversal via project names / asset paths (`sanitize_project_path`)
- Unsafe deserialization of `.storyproj` files
- Shell invocation of FFmpeg (`STORYVOICE_FFMPEG`) argument injection

## Hardening commitments

- No telemetry, no auto-executing remote content
- All downloads recorded with SHA256 and re-verified on launch
- Project files are JSON, parsed with the standard library only
