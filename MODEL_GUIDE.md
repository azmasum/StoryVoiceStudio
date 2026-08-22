# Model & Voice Guide

StoryVoice Studio separates **application licensing** from **model/voice
licensing**. Facts below are taken from the official sources listed — never
fabricated. Always re-verify at the source before commercial use.

## TTS engine

| Property | Value |
|----------|-------|
| Engine | [Piper](https://github.com/rhasspy/piper) (`piper-tts` Python package) |
| License | MIT |
| Commercial use | ✅ Yes (per upstream project) |
| Runs locally | ✅ ONNX on CPU; CUDA used automatically if available |

## Voices (US English)

Source repository: [rhasspy/piper-voices](https://github.com/rhasspy/piper-voices)
— the repository is licensed **MIT**.

| Voice ID | Gender | Style | Download size | License |
|----------|--------|-------|---------------|---------|
| en_US-lessac-medium | Female | Warm | ~63 MB | MIT |
| en_US-amy-medium | Female | Calm | ~63 MB | MIT |
| en_US-hfc_female-medium | Female | Documentary | ~63 MB | MIT |
| en_US-ryan-high | Male | Cinematic | ~118 MB | MIT |
| en_US-joe-medium | Male | Deep | ~63 MB | MIT |
| en_US-kusal-medium | Male | Serious | ~63 MB | MIT |
| en_US-danny-low | Male | Mystery | ~20 MB | MIT |

Download URLs point to `huggingface.co/rhasspy/piper-voices` (official mirror
of the same repository). The Model Manager shows each model's source URL and
license **before** download, records SHA256 checksums at install time, and
re-verifies them on launch.

> Note: individual voice training datasets may carry their own terms. Piper's
> authors release the voices under MIT; verify suitability for your specific
> commercial use case at the source link above when in doubt.

## COMMERCIAL-SAFE vs RESEARCH ONLY

| Category | Items in this repo |
|----------|--------------------|
| ✅ COMMERCIAL-SAFE (per current upstream licenses) | piper-tts engine, all cataloged piper-voices models |
| ⚠️ NON-COMMERCIAL / verify first | Any music or SFX files you import yourself |

The app never silently recommends research-only models for monetized content.
Future engines that are non-commercial will be labeled clearly in the Model
Manager and blocked from "commercial" presets with a warning.

## Voice cloning (future, opt-in)

The provider interface exposes `supports_voice_cloning()` so cloning engines
can plug in later. Policy:

1. Only clone voices you own or have explicit written permission to clone.
2. Display the target model's license before enabling.
3. No unauthorized impersonation — this is a hard product rule.
