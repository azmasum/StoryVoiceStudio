"""QThread worker that runs the generation pipeline off the UI thread."""
from __future__ import annotations

import traceback
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.generator import (
    CancelledError,
    GenerationOptions,
    GenerationOutcome,
    GenerationPipeline,
    ProgressState,
)
from app.utils.errors import UserFacingError


class GenerationWorker(QThread):
    progress_changed = Signal(object)          # ProgressState
    finished_ok = Signal(object)               # GenerationOutcome
    failed = Signal(str, str, list)            # what, why, actions
    cancelled = Signal()

    def __init__(
        self,
        project_name: str,
        project_dir: Path,
        options: GenerationOptions,
        script_text: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.script_text = script_text
        self.existing_chunks = None
        self.pipeline = GenerationPipeline(
            project_name=project_name,
            project_dir=project_dir,
            options=options,
            progress_callback=self._on_progress,
        )

    def _on_progress(self, state) -> None:
        """Pipeline progress callback - re-emitted as a cross-thread signal."""
        self.progress_changed.emit(state)

    def run(self) -> None:  # executes in worker thread
        try:
            outcome: GenerationOutcome = self.pipeline.run(
                self.script_text, existing_chunks=self.existing_chunks)
            self.finished_ok.emit(outcome)
        except CancelledError:
            self.cancelled.emit()
        except UserFacingError as error:
            self.failed.emit(error.what, error.why, error.actions)
        except Exception as error:  # noqa: BLE001 - final safety net
            traceback.print_exc()
            self.failed.emit(
                "Generation failed unexpectedly.",
                f"{error.__class__.__name__}: {error}",
                ["Check logs for technical details.",
                 "Try again; if it repeats, please report this issue."],
            )

    def pause(self) -> None:
        self.pipeline.pause()

    def resume(self) -> None:
        self.pipeline.resume()

    def cancel(self) -> None:
        self.pipeline.cancel()
