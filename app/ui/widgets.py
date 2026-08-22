"""Reusable UI widgets: waveform view and script statistics."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget

from audio.waveform.peaks import extract_peaks


class WaveformView(QWidget):
    """Lightweight waveform preview rendered from cached block peaks."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._peaks: list[float] = []
        self._playhead = 0.0  # 0..1
        self.setMinimumHeight(90)

    def set_audio(self, path: str | None) -> None:
        self._peaks = []
        self._playhead = 0.0
        if path:
            try:
                self._peaks = extract_peaks(path)
            except Exception:  # noqa: BLE001 - preview must never crash UI
                self._peaks = []
        self.update()

    def set_playhead(self, fraction: float) -> None:
        self._playhead = max(0.0, min(1.0, fraction))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt naming
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#141821"))
        width = self.width()
        height = self.height()
        mid = height / 2
        if not self._peaks:
            painter.setPen(QPen(QColor("#3a4356"), 1))
            painter.drawText(self.rect(), Qt.AlignCenter,
                             "No audio rendered yet")
            return
        count = len(self._peaks)
        pen_played = QPen(QColor("#4fc3f7"), 1)
        pen_rest = QPen(QColor("#5b6b8c"), 1)
        bar_width = max(1, width // count)
        for index, peak in enumerate(self._peaks):
            x = int(index * width / count)
            amplitude = max(1.0, peak * (height / 2 - 6))
            painter.setPen(pen_played if index / count <= self._playhead
                           else pen_rest)
            painter.drawLine(x, int(mid - amplitude), x,
                             int(mid + amplitude))


class ScriptEditor(QPlainTextEdit):
    """Script editor that reports text changes and supports markers."""

    text_changed_relaxed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setPlaceholderText(
            "Paste or write your story here...\n\n"
            "Markers: [SCENE: Night Street] [PAUSE:2] [EMOTION:FEAR] "
            "[WHISPER]"
        )
        self.textChanged.connect(self.text_changed_relaxed)

    def word_count(self) -> int:
        return len(self.toPlainText().split())

    def character_count(self) -> int:
        return len(self.toPlainText())


def make_stats_row() -> tuple[QWidget, dict[str, "object"]]:
    """Build the small stats strip under the editor."""
    from PySide6.QtWidgets import QHBoxLayout, QLabel

    container = QWidget()
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 2, 0, 2)
    labels: dict[str, object] = {}
    for key, title in (
        ("words", "Words"),
        ("chars", "Characters"),
        ("duration", "Est. duration"),
        ("wpm_actual", "Actual WPM"),
    ):
        label = QLabel(f"{title}: -")
        labels[key] = label
        layout.addWidget(label)
    layout.addStretch(1)
    return container, labels
