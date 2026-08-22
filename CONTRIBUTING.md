# Contributing to StoryVoice Studio

Thanks for helping build a free, private storytelling studio! 🎙️

## Ground rules

1. **No fake functionality.** Features must actually work or be clearly
   marked as future work in docs — never stubbed to look real.
2. **License honesty is sacred.** Model/music/SFX metadata must cite real
   sources. Never invent license facts or checksums.
3. **Offline-first.** Core features must not require internet or accounts.
4. **Users may see errors** only as `UserFacingError(what, why, actions)`.

## Workflow

1. Fork / create a branch (`feature/my-change`).
2. Make your change with tests:
   - `python -m pytest tests -q` must stay green.
3. Follow existing code style: type hints, docstrings on public APIs,
   one responsibility per module, no global mutable state.
4. Update CHANGELOG.md under an "Unreleased" section if user-visible.
5. Open a PR describing what & why; link related issues.

## Reporting bugs

Use the bug report template and attach logs from
Settings → Open Logs Folder (redact any personal content first).

## Suggesting features

Open a discussion/issue with the problem you're solving before writing code
for big changes (e.g., new TTS engine integrations).

## Adding AI models

Only via `models/registry.json` + official download URLs + verifiable
license metadata. See MODEL_GUIDE.md for policy.

## Code of Conduct

By participating you agree to the CODE_OF_CONDUCT.md.
