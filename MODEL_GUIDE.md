# Model & Voice Guide

StoryVoice Studio separates **application licensing** from **model/voice
licensing**. Facts below are taken from the official sources listed — never
fabricated. Always re-verify at the source before commercial use.

## TTS engines

### EdgeTTS (default) — free, keyless

| Property | Value |
|----------|-------|
| Engine | Microsoft Edge online TTS via `edge-tts` (unofficial keyless access) |
| License | Microsoft service terms — **verify before commercial use** |
| Commercial use | ⚠️ Verify Microsoft's terms first |
| Runs locally | ❌ Cloud service — needs internet, no key, no billing |
| Audio format | 24 kHz MP3 stream, decoded locally to 44.1 kHz WAV |
| Control | Real rate (±30%) and pitch (±40 Hz) knobs per chunk |

8 curated voices (verified live):

| Voice ID | Gender | Character |
|----------|--------|-----------|
| bn-BD-NabanitaNeural | Female | Bangladeshi Bengali, friendly |
| bn-BD-PradeepNeural | Male | Bangladeshi Bengali, friendly |
| en-US-AriaNeural | Female | News/Novel |
| en-US-JennyNeural | Female | General |
| en-US-EmmaMultilingualNeural | Female | Conversation |
| en-US-MichelleNeural | Female | News |
| en-US-GuyNeural | Male | News/Novel |
| en-US-AndrewMultilingualNeural | Male | Conversation |

Defaults: narrator **AriaNeural**, dialogue **GuyNeural**.

### Gemini (premium) — API key + billing

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
| ⚠️ VERIFY FIRST | EdgeTTS narration (Microsoft terms), any music/SFX you import |

The app never silently recommends research-only models for monetized content.

## Billing

EdgeTTS is free (no billing at all). Gemini usage is billed by Google per
AI Studio pricing (text in + audio out). Every generation reports its
characters + audio minutes; a typical 10-minute Gemini story costs a few
cents. Re-renders reuse cached chunks, so unchanged sentences are never
billed twice.
