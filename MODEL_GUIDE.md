# Model & Voice Guide

StoryVoice Studio separates **application licensing** from **model/voice
licensing**. Facts below are taken from the official sources listed — never
fabricated. Always re-verify at the source before commercial use.

## TTS engine

| Property | Value |
|----------|-------|
| Engine | Google Gemini API (`gemini-2.5-pro-preview-tts`, alt `gemini-2.5-flash-preview-tts`) |
| License | Gemini API Terms of Service (paid API) |
| Commercial use | ✅ Yes on the paid tier (verify current terms in your console) |
| Runs locally | ❌ Cloud API — needs internet + your own API key |
| Audio format | 24 kHz 16-bit PCM mono, SynthID-watermarked by Google |

Docs: <https://ai.google.dev/gemini-api/docs/speech-generation>
Keys: <https://aistudio.google.com/apikey>

## Voices (30 prebuilt studio voices)

Nothing is downloaded — every voice works on every model and in 70+
languages (auto-detected, incl. Bengali bn-BD). Steering is done with
natural-language style directions plus per-emotion delivery.

| Voice | Gender | Character |
|-------|--------|-----------|
| Zephyr | Female | Bright |
| Kore | Female | Firm |
| Leda | Female | Youthful |
| Aoede | Female | Breezy |
| Callirrhoe | Female | Easy-going |
| Autonoe | Female | Bright |
| Erinome | Female | Clear |
| Despina | Female | Smooth |
| Laomedeia | Female | Upbeat |
| Achernar | Female | Soft |
| Vindemiatrix | Female | Gentle |
| Sulafat | Female | Warm |
| Gacrux | Female | Versatile |
| Pulcherrima | Female | Versatile |
| Puck | Male | Upbeat |
| Charon | Male | Informative |
| Fenrir | Male | Excitable |
| Orus | Male | Firm |
| Enceladus | Male | Breathy |
| Iapetus | Male | Clear |
| Umbriel | Male | Easy-going |
| Algieba | Male | Smooth |
| Algenib | Male | Gravelly |
| Rasalgethi | Male | Informative |
| Alnilam | Male | Firm |
| Schedar | Male | Even |
| Achird | Male | Friendly |
| Zubenelgenubi | Male | Casual |
| Sadachbia | Male | Lively |
| Sadaltager | Male | Knowledgeable |

Defaults: narrator **Charon** (documentary), dialogue **Puck** (contrast).
Audition any voice from **Voices → Browse Voices** (plays a live sample).

## COMMERCIAL-SAFE vs RESEARCH ONLY

| Category | Items in this repo |
|----------|--------------------|
| ✅ COMMERCIAL-SAFE (per current upstream terms) | Gemini API paid-tier narration |
| ⚠️ NON-COMMERCIAL / verify first | Any music or SFX files you import yourself |

The app never silently recommends research-only models for monetized content.

## Billing

Usage is billed by Google per AI Studio pricing (text in + audio out).
Every generation reports its characters + audio minutes; a typical
10-minute story costs a few cents. Re-renders reuse cached chunks, so
unchanged sentences are never billed twice.
