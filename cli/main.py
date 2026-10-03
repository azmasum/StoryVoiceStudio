"""StoryVoice Studio command line interface (Gemini cloud voices).

Usage:
    storyvoice generate story.txt --voice Charon --dialogue-voice Puck
    storyvoice batch ./scripts/
    storyvoice voices
    storyvoice version

Needs a Gemini API key: set GEMINI_API_KEY or paste one in the app's
Voice panel (stored in local settings).
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from app.utils.errors import UserFacingError


def _add_generate_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("script", help="Path to a UTF-8 text script")
    parser.add_argument("--project-name", default="")
    parser.add_argument("--voice", default="en-US-AriaNeural",
                        help="Narrator voice (see `voices`)")
    parser.add_argument("--dialogue-voice", default="en-US-GuyNeural",
                        help="Voice for dialogue-heavy chunks")
    parser.add_argument("--engine", default="edge",
                        choices=["edge", "gemini"],
                        help="edge = free/keyless, gemini = API key + billing")
    parser.add_argument("--model", default="gemini-2.5-pro-preview-tts",
                        help="Gemini TTS model")
    parser.add_argument("--wpm", type=int, default=155)
    parser.add_argument("--emotion", default="auto",
                        help="'auto' or an emotion like FEAR, CALM, NEUTRAL")
    parser.add_argument("--preset", default="DOCUMENTARY",
                        help="Storytelling preset (see --list-presets)")
    parser.add_argument("--intensity", type=float, default=0.7)
    parser.add_argument("--music", default="", help="Background music file path")
    parser.add_argument("--music-gain-db", type=float, default=-18.0)
    parser.add_argument("--ducking-db", type=float, default=9.0)
    parser.add_argument("--loudness", default="YouTube",
                        choices=["YouTube", "Podcast", "Audiobook", "Cinematic"])
    parser.add_argument("--format", default="wav",
                        choices=["wav", "mp3", "flac"])
    parser.add_argument("--stems", action="store_true")
    parser.add_argument("--preview-seconds", type=float, default=0.0)
    parser.add_argument("--out-dir", default="", help="Directory for the project")
    parser.add_argument("--api-pacing", type=float, default=4.0,
                        help="Seconds between API requests (free-tier quota)")
    parser.add_argument("--api-key", default="",
                        help="Gemini API key (or GEMINI_API_KEY env)")


def build_parser() -> argparse.ArgumentParser:
    from emotion.presets import preset_names

    parser = argparse.ArgumentParser(
        prog="storyvoice",
        description="Gemini-powered AI storytelling audio studio.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate audio for one script")
    _add_generate_args(gen)

    batch = sub.add_parser("batch", help="Generate audio for every .txt in a folder")
    batch.add_argument("folder", help="Folder containing .txt scripts")
    _add_shared_options(batch)

    voices = sub.add_parser("voices", help="List the 30 Gemini voices")

    presets = sub.add_parser("presets", help="List storytelling presets")

    ver = sub.add_parser("version", help="Print version")
    _ = presets, ver
    return parser


def _add_shared_options(parser: argparse.ArgumentParser) -> None:
    pass  # shared flags live on each subparser for now


def cmd_generate(args: argparse.Namespace) -> int:
    from app.core.generator import GenerationOptions, GenerationPipeline
    from app.config.paths import projects_dir, sanitize_project_path

    script_path = Path(args.script)
    if not script_path.exists():
        print(f"Script not found: {script_path}")
        return 2
    script_text = script_path.read_text(encoding="utf-8")

    api_key = args.api_key or os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        from app.config.settings import load_settings, save_settings

        settings = load_settings()
        if not settings.gemini_api_key:
            settings.gemini_api_key = api_key
            save_settings(settings)

    name = args.project_name or script_path.stem
    project_dir = sanitize_project_path(projects_dir(), name)
    project_dir.mkdir(parents=True, exist_ok=True)

    auto_emotion = args.emotion.lower() == "auto"
    forced_emotion = "" if auto_emotion else args.emotion.upper()

    options = GenerationOptions(
        voice_id=args.voice,
        dialogue_voice=args.dialogue_voice,
        gemini_model=args.model,
        engine=args.engine,
        target_wpm=args.wpm,
        preset_key=args.preset,
        auto_emotion=auto_emotion or bool(forced_emotion),
        emotion_intensity=args.intensity,
        api_pacing_seconds=args.api_pacing,
        music_path=args.music,
        music_gain_db=args.music_gain_db,
        ducking_db=args.ducking_db,
        loudness_preset=args.loudness,
        export_format=args.format,
        export_stems=args.stems,
        preview_seconds=args.preview_seconds,
    )
    if not auto_emotion:
        script_text = "\n".join(
            f"[EMOTION:{forced_emotion}]{line}" for line in script_text.splitlines()
            if line.strip()
        )

    pipeline = GenerationPipeline(name, project_dir, options,
                                  progress_callback=_cli_progress)
    outcome = pipeline.run(script_text)
    for path in outcome.output_paths:
        print(f"Exported: {path}")
    api_note = ""
    if outcome.stats.get("api_chars"):
        api_note = (f", API: {outcome.stats['api_chars']:,} chars, "
                    f"{outcome.stats.get('api_audio_seconds', 0) / 60.0:.1f} "
                    f"min audio")
    print(
        f"Done. {outcome.chunk_count_done}/{outcome.chunk_count_total} chunks, "
        f"{outcome.duration_seconds:.1f}s, {outcome.actual_wpm} WPM actual, "
        f"{outcome.lufs} LUFS{api_note}."
    )
    return 0


def _cli_progress(state) -> None:
    if state.phase in ("voice", "mix", "export"):
        pct = state.overall_percent
        eta = int(state.eta_seconds)
        sys.stdout.write(
            f"\r[{state.phase:>6}] {pct:5.1f}%  chunk {state.chunk_index}/"
            f"{state.chunk_count}  ETA {eta}s   "
        )
        sys.stdout.flush()


def cmd_batch(args: argparse.Namespace) -> int:
    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"Folder not found: {folder}")
        return 2
    scripts = sorted(folder.glob("*.txt"))
    if not scripts:
        print(f"No .txt files found in {folder}")
        return 2
    failures = 0
    total = len(scripts)
    for index, script in enumerate(scripts, start=1):
        print(f"\n=== Queue {index:02d}/{total:02d}: {script.name} ===")
        args.script = str(script)
        args.project_name = script.stem
        try:
            code = cmd_generate(args)
        except Exception as exc:  # noqa: BLE001 - keep the queue running
            logging.getLogger(__name__).exception("Batch item failed")
            print(f"FAILED: {exc}")
            code = 1
        if code != 0:
            failures += 1
    print(f"\nBatch complete: {total - failures}/{total} succeeded.")
    return 0 if failures == 0 else 1


def cmd_voices(args: argparse.Namespace) -> int:
    from tts.voices.catalog import voices_for_engine

    for engine, title in (("edge", "EdgeTTS (free, no key)"),
                          ("gemini", "Gemini (API key + billing)")):
        print(f"\n{title}:")
        print(f"{'VOICE':34} {'GENDER':7} {'CHARACTER':12}  LICENSE")
        for entry in voices_for_engine(engine):
            print(f"{entry['voice_id']:34} {entry['gender']:7} "
                  f"{entry['style']:12}  {entry['license'][:60]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    from app.utils.logging_setup import setup_logging

    setup_logging()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            return cmd_generate(args)
        if args.command == "batch":
            return cmd_batch(args)
        if args.command == "voices":
            return cmd_voices(args)
        if args.command == "version":
            from app.version import APP_NAME, VERSION

            print(f"{APP_NAME} v{VERSION}")
            return 0
        parser.print_help()
        return 2
    except UserFacingError as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
