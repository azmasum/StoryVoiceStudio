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

    from app.utils.hardware import detect_hardware

    _ = detect_hardware()  # logs capabilities early; never fatal on failure

    from app.ui.main_window import MainWindow

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
