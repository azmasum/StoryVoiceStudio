"""Dialogs: Voices browser, Settings, About, First-Run Wizard, Update."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from app.config.settings import AppSettings
from app.utils.hardware import HardwareInfo, detect_hardware
from app.version import APP_NAME, APP_TAGLINE, COMMERCIAL_WARNING, PRIVACY_NOTICE, VERSION


class _SampleThread(QThread):
    done = Signal(str)
    failed = Signal(str, str, list)

    def __init__(self, voice: str, model: str, parent=None) -> None:
        super().__init__(parent)
        self.voice = voice
        self.model = model

    def run(self) -> None:  # pragma: no cover - Qt thread entry
        try:
            import tempfile

            from tts.manager import get_provider
            from tts.voices.catalog import get_engine

            engine = get_engine(self.voice)
            provider = get_provider(engine)
            if engine == "gemini" and hasattr(provider, "configure"):
                from app.config.settings import load_settings

                settings = load_settings()
                provider.configure(settings.gemini_api_key,
                                   self.model or settings.gemini_model)
            out = Path(tempfile.gettempdir()) / f"svs-sample-{self.voice}.wav"
            if hasattr(provider, "synthesize_with_style"):
                provider.synthesize_with_style(
                    "Hello! This is a short voice sample for your story.",
                    out, self.voice, "NEUTRAL", "DOCUMENTARY", 0.7)
            else:
                provider.synthesize(
                    "Hello! This is a short voice sample.", out, self.voice)
            self.done.emit(str(out))
        except Exception as error:  # noqa: BLE001
            from app.utils.errors import report_exception

            friendly = report_exception(error)
            self.failed.emit(friendly.what, friendly.why, friendly.actions)


class ModelManagerDialog(QDialog):
    """Browse the 30 Gemini voices, manage the API key, audition voices."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Voices")
        self.resize(720, 560)
        self._thread: _SampleThread | None = None
        self._player = None

        from app.config.settings import load_settings

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "<b>38 voices, two engines</b> - EdgeTTS is free with no key; "
            "Gemini voices need an API key and are billed by Google. "
            "Nothing to download."))

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        rows = ["<tr><th>Voice</th><th>Gender</th><th>Character</th></tr>"]
        from tts.voices.gemini_catalog import CATALOG_VOICES

        for entry in CATALOG_VOICES:
            rows.append(
                f"<tr><td>{entry['voice_id']}</td>"
                f"<td>{entry['gender']}</td>"
                f"<td>{entry['style']}</td></tr>")
        browser.setHtml("<table border=1 cellspacing=0 cellpadding=4 "
                        "width='100%'>" + "".join(rows) + "</table>")
        layout.addWidget(browser, 1)

        # -- API key ------------------------------------------------------
        key_row = QHBoxLayout()
        key_row.addWidget(QLabel("API key:"))
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("Paste key from aistudio.google.com")
        self.key_edit.setText(load_settings().gemini_api_key)
        save_btn = QPushButton("Save key")
        save_btn.setFixedWidth(90)
        save_btn.clicked.connect(self._save_key)
        key_row.addWidget(self.key_edit, 1)
        key_row.addWidget(save_btn)
        layout.addLayout(key_row)
        key_hint = QLabel(
            '<a href="https://aistudio.google.com/apikey">Get a key at '
            "AI Studio</a> - stored in local settings only, never logged.")
        key_hint.setOpenExternalLinks(True)
        layout.addWidget(key_hint)

        # -- Audition ------------------------------------------------------
        from tts.voices.gemini_catalog import GEMINI_MODELS

        sample_row = QHBoxLayout()
        sample_row.addWidget(QLabel("Audition:"))
        self.sample_voice = QComboBox()
        for entry in CATALOG_VOICES:
            self.sample_voice.addItem(entry["name"], entry["voice_id"])
        self.sample_model = QComboBox()
        self.sample_model.addItems(list(GEMINI_MODELS))
        play_btn = QPushButton("Play sample")
        play_btn.clicked.connect(self._play_sample)
        sample_row.addWidget(self.sample_voice, 1)
        sample_row.addWidget(self.sample_model)
        sample_row.addWidget(play_btn)
        layout.addLayout(sample_row)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save_key(self) -> None:
        from app.config.settings import load_settings, save_settings
        from tts.manager import reset_provider

        settings = load_settings()
        settings.gemini_api_key = self.key_edit.text().strip()
        save_settings(settings)
        reset_provider("gemini")
        self.status.setText("API key saved locally.")
        self.status.setStyleSheet("color: #7fbf7f;")

    def _play_sample(self) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        voice = self.sample_voice.currentData()
        model = self.sample_model.currentText()
        self.status.setText(f"Synthesizing {voice} sample...")
        self.status.setStyleSheet("")
        self._thread = _SampleThread(voice, model, self)
        self._thread.done.connect(self._on_sample)
        self._thread.failed.connect(self._on_sample_failed)
        self._thread.start()

    def _on_sample(self, path: str) -> None:
        self.status.setText(f"Sample ready: {path}")
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

            if self._player is None:
                self._player = QMediaPlayer(self)
                self._player.setAudioOutput(QAudioOutput(self))
            self._player.setSource(QUrl.fromLocalFile(path))
            self._player.play()
        except Exception:  # noqa: BLE001 - playback is best-effort
            pass

    def _on_sample_failed(self, what: str, why: str, actions: list) -> None:
        self.status.setText(what)
        QMessageBox.warning(self, "Sample failed",
                            f"{what}\n\nWhy: {why}\n\n" + "\n".join(actions))


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"About {APP_NAME}")
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setHtml(
            f"<h2>{APP_NAME} v{VERSION}</h2>"
            f"<p>{APP_TAGLINE}</p>"
            f"<p>{PRIVACY_NOTICE}</p>"
            "<p>No analytics. No hidden telemetry.</p>"
            "<p>Narration uses the Google Gemini API (your own API key, "
            "billed by Google). Generated audio carries a SynthID watermark "
            "applied by Google.</p>"
            "<p>Application code: MIT license. AI voices are governed by "
            "the Gemini API Terms of Service - see LICENSES.md.</p>"
        )
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


class CheckUpdatesDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Check for Updates")
        self.info_label = QLabel("Checking GitHub Releases...")
        self.download_btn = QPushButton("Download")
        self.download_btn.setVisible(False)
        later_btn = QPushButton("Later")
        self.url = ""

        layout = QVBoxLayout(self)
        layout.addWidget(self.info_label)
        row = QHBoxLayout()
        row.addWidget(self.download_btn)
        row.addWidget(later_btn)
        layout.addLayout(row)
        self.download_btn.clicked.connect(self._open_download)
        later_btn.clicked.connect(self.reject)
        self._check()

    def _check(self) -> None:
        from app.utils.updates import check_for_update

        info = check_for_update()
        if info.error:
            self.info_label.setText(info.error)
        elif info.available:
            self.info_label.setText(
                f"StoryVoice Studio v{info.latest_version} is available.")
            self.url = info.download_url
            self.download_btn.setVisible(bool(self.url))
        else:
            self.info_label.setText(
                f"You are running the latest version (v{VERSION}).")

    def _open_download(self) -> None:
        if self.url:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl as _QUrl

            QDesktopServices.openUrl(_QUrl(self.url))


class FirstRunWizard(QDialog):
    """API key setup on first launch."""

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.hardware: HardwareInfo | None = None
        self.setWindowTitle(f"Welcome to {APP_NAME}")
        self.resize(560, 420)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok |
                                   QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        hardware = detect_hardware()
        self.hardware = hardware
        browser.setHtml(
            "<h3>Welcome!</h3>"
            "<p>StoryVoice Studio narrates your stories with natural AI "
            "voices - in English, Bengali and 70+ more languages.</p>"
            "<h4>Free path (recommended)</h4>"
            "<p>Just press OK: the built-in EdgeTTS engine is completely "
            "free, no key and no billing. Pick a voice and press "
            "GENERATE.</p>"
            "<h4>Premium path (optional)</h4>"
            "<p>For Gemini studio voices, get a key at "
            '<a href="https://aistudio.google.com/apikey">AI Studio</a> '
            "and paste it into the Voice panel's <b>API key</b> field, then "
            "switch Engine to Gemini. Usage is billed by Google - a typical "
            "10-minute story costs a few cents.</p>"
            f"<p style='color:#d9a441'>{COMMERCIAL_WARNING}</p>"
        )
