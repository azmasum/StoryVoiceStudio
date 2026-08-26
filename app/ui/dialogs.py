"""Dialogs: Model Manager, Settings, About, First-Run Wizard, Update."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from app.config.settings import AppSettings
from app.utils.hardware import HardwareInfo, detect_hardware
from app.version import APP_NAME, APP_TAGLINE, COMMERCIAL_WARNING, PRIVACY_NOTICE, VERSION
from models.downloader import install_voice
from models.manager import list_models


class _DownloadThread(QThread):
    progress = Signal(str, int, int)
    done = Signal(str)
    failed = Signal(str, str, list)

    def __init__(self, voice_id: str, parent=None) -> None:
        super().__init__(parent)
        self.voice_id = voice_id

    def run(self) -> None:  # pragma: no cover - Qt thread entry
        try:
            install_voice(self.voice_id,
                          lambda stage, d, t: self.progress.emit(stage, d, t))
            self.done.emit(self.voice_id)
        except Exception as error:  # noqa: BLE001
            from app.utils.errors import report_exception

            friendly = report_exception(error)
            self.failed.emit(friendly.what, friendly.why, friendly.actions)


class ModelManagerDialog(QDialog):
    """Install/remove AI voice models; shows licenses before download."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Model Manager")
        self.resize(720, 620)
        self._thread: _DownloadThread | None = None

        layout = QVBoxLayout(self)
        self.table_label = QLabel()
        layout.addWidget(self._build_table())

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.status = QLabel(
            "Downloads come only from official sources shown above. "
            "SHA256 checksums are computed and verified on install."
        )
        self.status.setWordWrap(True)
        layout.addWidget(self.progress)
        layout.addWidget(self.status)

        # -- Voice Modules (cloned voice presets) --------------------------
        sep = QLabel("<b>Voice Modules</b> (saved cloned voices)")
        sep.setWordWrap(True)
        layout.addWidget(sep)

        mod_row = QHBoxLayout()
        self.mod_ref_edit = QLineEdit()
        self.mod_ref_edit.setPlaceholderText("Reference .wav / .mp3 (file or URL)")
        browse_btn = QPushButton("Browse...")
        browse_btn.setFixedWidth(80)
        browse_btn.clicked.connect(self._browse_module_ref)
        mod_row.addWidget(self.mod_ref_edit, 1)
        mod_row.addWidget(browse_btn)
        layout.addLayout(mod_row)

        save_row = QHBoxLayout()
        self.mod_name_edit = QLineEdit()
        self.mod_name_edit.setPlaceholderText("Module name (e.g. My Voice)")
        self.mod_tau_combo = QComboBox()
        self.mod_tau_combo.addItems(["0.3 (gentle)", "0.5 (moderate)", "0.7 (strong)"])
        save_btn = QPushButton("Save Module")
        save_btn.clicked.connect(self._save_module)
        save_row.addWidget(self.mod_name_edit, 2)
        save_row.addWidget(QLabel("Strength:"))
        save_row.addWidget(self.mod_tau_combo)
        save_row.addWidget(save_btn)
        layout.addLayout(save_row)

        self.mod_status = QLabel()
        self.mod_status.setWordWrap(True)
        layout.addWidget(self.mod_status)

        self.modules_browser = QTextBrowser()
        self.modules_browser.setOpenLinks(False)
        self.modules_browser.setMaximumHeight(160)
        self.modules_browser.anchorClicked.connect(self._module_link)
        layout.addWidget(self.modules_browser)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.clicked.connect(lambda _: self.refresh())
        layout.addWidget(buttons)
        self.refresh()

    def _build_table(self) -> QTextBrowser:
        self.table = QTextBrowser()
        self.table.setOpenExternalLinks(True)
        return self.table

    def refresh(self) -> None:
        rows = [
            "<tr><th>Model</th><th>Size</th><th>License</th><th>Commercial</th>"
            "<th>Status</th><th>Source</th><th></th></tr>"
        ]
        for model in list_models():
            status = ("installed" + ("" if model.verified else " (unverified)")
                      if model.installed else "not installed")
            action = ""
            if model.installed:
                action = f'<a href="remove:{model.model_id}">Remove</a>'
            else:
                action = f'<a href="install:{model.model_id}">Download</a>'
            rows.append(
                f"<tr><td>{model.name}</td>"
                f"<td>{model.size_mb:.0f} MB</td>"
                f"<td>{model.license}</td>"
                f"<td>{'YES' if model.commercial_use else 'NO'}</td>"
                f"<td>{status}</td>"
                f'<td><a href="{model.source_url}">official source</a></td>'
                f"<td>{action}</td></tr>"
            )
        html = (
            "<p>" + COMMERCIAL_WARNING + "</p>"
            "<table border=1 cellspacing=0 cellpadding=4 width='100%'>"
            + "".join(rows) + "</table>"
            f"<p>{PRIVACY_NOTICE}</p>"
        )
        self.table.setHtml(html)
        self.table.anchorClicked.connect(self._handle_link)
        self._refresh_modules()

    def _handle_link(self, url) -> None:
        text = url.toString()
        if text.startswith("install:"):
            self._start_download(text.split(":", 1)[1])
        elif text.startswith("remove:"):
            from models.downloader import remove_voice

            remove_voice(text.split(":", 1)[1])
            self.refresh()

    def _start_download(self, voice_id: str) -> None:
        if self._thread is not None and self._thread.isRunning():
            return
        license_ok = QMessageBox.question(
            self, "Confirm license",
            f"Download {voice_id}?\n\nLicense: MIT "
            "(rhasspy/piper-voices). Commercial use permitted. Continue?",
        )
        if license_ok != QMessageBox.Yes:
            return
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self.status.setText(f"Downloading {voice_id}...")
        self._thread = _DownloadThread(voice_id, self)
        self._thread.progress.connect(self._on_progress)
        self._thread.done.connect(self._on_done)
        self._thread.failed.connect(self._on_failed)
        self._thread.start()

    def _on_progress(self, stage: str, done: int, total: int) -> None:
        percent = int(done / total * 100) if total else 0
        self.progress.setValue(percent)
        self.status.setText(f"{stage}: {done}/{total} bytes")

    def _on_done(self, voice_id: str) -> None:
        self.progress.setVisible(False)
        self.status.setText(f"Installed {voice_id}.")
        self.refresh()

    def _on_failed(self, what: str, why: str, actions: list) -> None:
        self.progress.setVisible(False)
        self.status.setText(what)
        QMessageBox.warning(self, "Download failed",
                            f"{what}\n\nWhy: {why}\n\n" + "\n".join(actions))

    def _browse_module_ref(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select reference voice clip", "",
            "Audio (*.wav *.mp3 *.flac *.ogg)")
        if path:
            self.mod_ref_edit.setText(path)

    def _save_module(self) -> None:
        from models.voice_modules import save_module, load_modules

        name = self.mod_name_edit.text().strip()
        ref = self.mod_ref_edit.text().strip()
        if not name:
            self.mod_status.setText("Enter a module name.")
            self.mod_status.setStyleSheet("color: #d9776b;")
            return
        if not ref:
            self.mod_status.setText("Browse for a reference audio file first.")
            self.mod_status.setStyleSheet("color: #d9776b;")
            return
        ref_path = Path(ref)
        if ref.startswith("http://") or ref.startswith("https://"):
            try:
                from audio.clone import engine as clone_engine
                from app.config.paths import references_dir
                local = clone_engine.load_reference(ref, references_dir())
                ref_path = local
            except Exception as exc:
                self.mod_status.setText(f"Download failed: {exc}")
                self.mod_status.setStyleSheet("color: #d9776b;")
                return
        if not ref_path.exists():
            self.mod_status.setText(f"File not found: {ref_path}")
            self.mod_status.setStyleSheet("color: #d9776b;")
            return
        tau_text = self.mod_tau_combo.currentText()
        tau = float(tau_text.split("(")[0].strip())
        try:
            save_module(name, ref_path, tau=tau)
        except ValueError as exc:
            self.mod_status.setText(str(exc))
            self.mod_status.setStyleSheet("color: #d9776b;")
            return
        self.mod_status.setText(f"Saved '{name}'. Now appears in Voice dropdown.")
        self.mod_status.setStyleSheet("color: #7fbf7f;")
        self.mod_name_edit.clear()
        self.mod_ref_edit.clear()
        self._refresh_modules()

    def _refresh_modules(self) -> None:
        from models.voice_modules import load_modules

        modules = load_modules()
        if not modules:
            self.modules_browser.setHtml(
                "<p style='color:#8a93a6'>No saved modules yet.</p>")
            return
        rows = ["<tr><th>Name</th><th>Created</th><th>Strength</th><th></th></tr>"]
        for m in modules:
            created = m.created_at[:10] if m.created_at else "-"
            rows.append(
                f"<tr><td>{m.name}</td><td>{created}</td>"
                f"<td>{m.tau}</td>"
                f'<td><a href="delete:{m.name}">Delete</a></td></tr>')
        html = ("<table border=1 cellspacing=0 cellpadding=4 width='100%'>"
                + "".join(rows) + "</table>")
        self.modules_browser.setHtml(html)

    def _module_link(self, url) -> None:
        text = url.toString()
        if text.startswith("delete:"):
            name = text.split(":", 1)[1]
            from models.voice_modules import delete_module
            if delete_module(name):
                self.mod_status.setText(f"Deleted '{name}'.")
                self.mod_status.setStyleSheet("color: #8a93a6;")
            self._refresh_modules()


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
            "<p>No analytics. No hidden telemetry. No cloud dependency.</p>"
            "<p>Application code: MIT license. AI models, voices, music and "
            "SFX have separate licenses - see LICENSES.md.</p>"
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
            from PySide6.QtCore import QUrl

            QDesktopServices.openUrl(QUrl(self.url))


class FirstRunWizard(QDialog):
    """Hardware detection + engine/voice choice on first launch."""

    def __init__(self, settings: AppSettings, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.hardware: HardwareInfo | None = None
        self.setWindowTitle(f"Welcome to {APP_NAME}")
        self.resize(560, 420)
        layout = QVBoxLayout(self)
        browser = QTextBrowser()
        browser.setOpenLinks(False)
        browser.anchorClicked.connect(self._link)
        layout.addWidget(browser)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok |
                                   QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        hardware = detect_hardware()
        self.hardware = hardware
        gpu_text = hardware.gpu_name or "None (CPU MODE)"
        quality = hardware.recommended_quality
        browser.setHtml(
            "<h3>Welcome!</h3>"
            "<p>This wizard sets up local AI storytelling on your PC.</p>"
            f"<h4>Your hardware</h4>"
            f"<ul><li>CPU: {hardware.cpu_name} ({hardware.cpu_cores} cores)</li>"
            f"<li>RAM: {hardware.ram_gb:.1f} GB</li>"
            f"<li>GPU: {gpu_text}"
            + (f" ({hardware.vram_gb:.1f} GB VRAM)" if hardware.gpu_name else "")
            + "</li></ul>"
            f"<p><b>Recommended quality:</b> {quality}</p>"
            "<h4>TTS engine</h4>"
            "<p>Piper (local neural TTS, CPU-friendly). Voices are MIT "
            "licensed from the official rhasspy/piper-voices repository.</p>"
            "<h4>Next step</h4>"
            f"<p>Download a starter voice (~63 MB): "
            '<a href="model:en_US-lessac-medium">Install en_US-lessac-medium'
            "</a> — or open <b>Models → Model Manager</b> any time.</p>"
            f"<p style='color:#d9a441'>{COMMERCIAL_WARNING}</p>"
        )

    def _link(self, url) -> None:
        text = url.toString()
        if text.startswith("model:"):
            voice_id = text.split(":", 1)[1]
            self._thread = _DownloadThread(voice_id, self)
            self._thread.done.connect(
                lambda v: QMessageBox.information(self, "Done",
                                                  f"Installed {v}."))
            self._thread.failed.connect(self._download_failed)
            self._thread.start()

    @staticmethod
    def _download_failed(what: str, why: str, actions: list) -> None:
        QMessageBox.warning(None, "Download failed",
                            f"{what}\n\nWhy: {why}\n\n" + "\n".join(actions))
