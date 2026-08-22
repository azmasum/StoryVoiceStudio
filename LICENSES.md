# LICENSES

## Application code

StoryVoice Studio source code is licensed under the **MIT License** — see
[LICENSE](LICENSE).

## Third-party runtime components

| Component | License | Source |
|-----------|---------|--------|
| PySide6 / Qt 6 | LGPLv3 (used dynamically) | qt.io |
| NumPy | BSD-3 | numpy.org |
| SciPy | BSD-3 | scipy.org |
| libsndfile (via soundfile) | LGPL-2.1 | libsndfile.github.io |
| pyloudnorm | MIT | github.com/csteinmetz1/pyloudnorm |
| piper-tts | MIT | github.com/rhasspy/piper |
| onnxruntime | MIT | onnxruntime.ai |
| FFmpeg (optional, user-installed) | GPL/LGPL depending on build | ffmpeg.org |

Qt is used through its LGPL-licensed dynamic linking; StoryVoice Studio ships
no statically linked Qt. FFmpeg is never bundled; users install their own
build and the app only shells out to it.

## AI models & voices

See [MODEL_GUIDE.md](MODEL_GUIDE.md). Engine and voices are MIT licensed by
their upstream projects. Model files are downloaded at runtime from official
sources with checksum recording — they are **not** part of this repository.

## Music & SFX

**Nothing is bundled.** You import your own audio. You are responsible for
holding rights appropriate to your use (e.g., monetized YouTube).

## Summary

> Before publishing monetized content, verify that your selected AI model,
> voice, music and SFX licenses permit commercial use.
