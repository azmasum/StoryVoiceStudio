"""StoryVoice Studio entry point.

    python -m app.main          -> launch the GUI
    python -m app.main --cli .. -> forward to the CLI
"""
from __future__ import annotations

import sys


def main() -> int:
    from app.utils.logging_setup import setup_logging

    setup_logging()

    if "--cli" in sys.argv:
        index = sys.argv.index("--cli")
        argv = sys.argv[index + 1:]
        from cli.main import main as cli_main

        return cli_main(argv)

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "PySide6 is not installed. Run:\n"
            "  pip install -r requirements.txt\n"
            "or double-click run_dev.bat"
        )
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("StoryVoice Studio")
    from app.version import APP_NAME, VERSION

    app.setApplicationVersion(VERSION)
    app.setOrganizationName(APP_NAME)

    # Qt swallows exceptions raised inside slots; route them to the log
    # and stderr so button handlers can never fail silently.
    def _qt_excepthook(exc_type, exc, tb) -> None:
        from app.utils.errors import report_exception

        report_exception(exc, context="GUI slot")
        sys.__excepthook__(exc_type, exc, tb)

    sys.excepthook = _qt_excepthook

    from app.utils.hardware import detect_hardware

    _ = detect_hardware()  # logs capabilities early; never fatal on failure

    # Voices shipped inside the app package become "installed" on first
    # run, so the Model Manager shows them without any download.
    try:
        from models.bundled import seed_bundled_voices

        seeded = seed_bundled_voices()
        if seeded:
            from app.utils.logging_setup import get_logger

            get_logger(__name__).info(
                "Seeded %d bundled voice(s): %s", len(seeded),
                ", ".join(seeded))
    except Exception:  # noqa: BLE001 - downloads remain a fallback
        import logging

        logging.getLogger(__name__).exception(
            "Bundled-voice seeding failed; continuing")

    from app.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
