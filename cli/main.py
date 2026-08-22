"""StoryVoice Studio command line interface.

Usage:
    storyvoice generate story.txt --voice en_US-lessac-medium --wpm 155
    storyvoice batch ./scripts/
    storyvoice voices
    storyvoice download-model en_US-ryan-high
    storyvoice version
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from app.utils.errors import UserFacingError


def _add_generate_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("script", help="Path to a UTF-8 text script")
    parser.add_argument("--project-name", default="")
    parser.add_argument("--voice", default="en_US-lessac-medium")
    parser.add_argument("--engine", default="piper")
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


def build_parser() -> argparse.ArgumentParser:
    from emotion.presets import preset_names

    parser = argparse.ArgumentParser(
        prog="storyvoice",
        description="Local, offline AI storytelling audio studio.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate audio for one script")
    _add_generate_args(gen)

    batch = sub.add_parser("batch", help="Generate audio for every .txt in a folder")
    batch.add_argument("folder", help="Folder containing .txt scripts")
    _add_shared_options(batch)

    voices = sub.add_parser("voices", help="List available US English voices")
    voices.add_argument("--installed-only", action="store_true")

    dl = sub.add_parser("download-model", help="Download a voice model")
    dl.add_argument("voice_id")

    models = sub.add_parser("models", help="Show model status and licenses")

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

    name = args.project_name or script_path.stem
    project_dir = sanitize_project_path(projects_dir(), name)
    project_dir.mkdir(parents=True, exist_ok=True)

    auto_emotion = args.emotion.lower() == "auto"
    forced_emotion = "" if auto_emotion else args.emotion.upper()

    options = GenerationOptions(
        voice_id=args.voice,
        engine=args.engine,
        target_wpm=args.wpm,
        preset_key=args.preset,
        auto_emotion=auto_emotion or bool(forced_emotion),
        emotion_intensity=args.intensity,
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
    print(
        f"Done. {outcome.chunk_count_done}/{outcome.chunk_count_total} chunks, "
        f"{outcome.duration_seconds:.1f}s, {outcome.actual_wpm} WPM actual "
        f"({args.wpm} target), {outcome.lufs} LUFS."
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
    from models.downloader import is_voice_installed
    from tts.voices.catalog import CATALOG_VOICES

    print(f"{'VOICE ID':28} {'GENDER':7} {'STYLE':12} {'SIZE':>7}  INSTALLED  LICENSE")
    for entry in CATALOG_VOICES:
        installed = is_voice_installed(entry["voice_id"])
        if args.installed_only and not installed:
            continue
        marker = "yes" if installed else "no"
        print(f"{entry['voice_id']:28} {entry['gender']:7} {entry['style']:12} "
              f"{entry['model_size_mb']:>5.0f}MB  {marker:<9}  {entry['license']}")
    return 0


def cmd_models(_args: argparse.Namespace) -> int:
    from models.manager import list_models

    for model in list_models():
        state = "INSTALLED" + ("" if model.verified else " (unverified)") \
            if model.installed else "not installed"
        print(f"- {model.model_id} [{state}] license={model.license} "
              f"commercial={'YES' if model.commercial_use else 'NO'}")
        print(f"  source: {model.source_url}")
    return 0


def cmd_download_model(args: argparse.Namespace) -> int:
    from models.downloader import install_voice

    def progress(stage: str, done: int, total: int) -> None:
        pct = done / total * 100 if total else 0
        sys.stdout.write(f"\r{stage}: {pct:5.1f}% ({done}/{total} bytes)")
        sys.stdout.flush()

    install_voice(args.voice_id, progress)
    print(f"\nInstalled {args.voice_id}.")
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
        if args.command == "models":
            return cmd_models(args)
        if args.command == "download-model":
            return cmd_download_model(args)
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
