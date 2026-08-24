"""StoryVoice Studio main window (PySide6, dark professional UI)."""
from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon, QKeySequence
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.config.paths import projects_dir, sanitize_project_path
from app.config.settings import AppSettings, load_settings, save_settings
from app.core.generator import GenerationOptions, GenerationOutcome
from app.ui.dialogs import (
    AboutDialog,
    CheckUpdatesDialog,
    FirstRunWizard,
    ModelManagerDialog,
)
from app.ui.panels import ControlsPanel
from app.ui.widgets import ScriptEditor, WaveformView, make_stats_row
from app.utils.errors import UserFacingError
from app.utils.logging_setup import get_logger, open_logs_folder
from app.version import APP_NAME, COMMERCIAL_WARNING, PRIVACY_NOTICE, VERSION
from app.workers.generation_worker import GenerationWorker
from project.autosave import (
    AutosaveManager,
    discard_snapshot,
    has_recovery_snapshot,
    recover,
)
from project.database import StoryProject, load_project, save_project

log = get_logger("app")

DARK_STYLE = """
QWidget { background-color: #1b2130; color: #dfe6f3; font-size: 13px; }
QGroupBox { border: 1px solid #2c3550; border-radius: 6px;
            margin-top: 10px; padding-top: 6px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; color: #8fa3c8; }
QPushButton { background-color: #2c3550; border-radius: 4px;
              padding: 5px 12px; }
QPushButton:hover { background-color: #38436b; }
QPushButton#generateBtn { background-color: #2e7d32; font-weight: bold;
                          font-size: 16px; padding: 12px; }
QPushButton#generateBtn:hover { background-color: #388e3c; }
QPlainTextEdit { background-color: #141a26; border: 1px solid #2c3550; }
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
    background-color: #141a26; border: 1px solid #2c3550; padding: 3px; }
QProgressBar { border: 1px solid #2c3550; border-radius: 3px;
               text-align: center; }
QProgressBar::chunk { background-color: #4fc3f7; }
QStatusBar { background: #161c29; }
"""


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings: AppSettings = load_settings()
        self.project = StoryProject(name="Untitled Story")
        self.project_path: Path | None = None
        self.worker: GenerationWorker | None = None
        self.last_outcome: GenerationOutcome | None = None
        self.autosave = AutosaveManager(self.settings.autosave_seconds)

        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.resize(1400, 860)
        self.setStyleSheet(DARK_STYLE)
        self._build_menus()
        self._build_ui()
        self._build_statusbar()
        self._build_autosave_timer()

        if not self.settings.simple_mode:
            self._set_advanced_visible(True)

        QTimer.singleShot(150, self._first_run_check)

    # -- construction ---------------------------------------------------------

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        new_action = QAction("&New Project", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._new_project)
        open_action = QAction("&Open Project...", self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._open_project)
        save_action = QAction("&Save Project", self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(self._save_project)
        save_as = QAction("Save Project &As...", self)
        save_as.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as.triggered.connect(self._save_project_as)
        import_txt = QAction("&Import Script (TXT)...", self)
        import_txt.triggered.connect(self._import_script)
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        for action in (new_action, open_action, save_action, save_as,
                       import_txt, exit_action):
            file_menu.addAction(action)

        project_menu = self.menuBar().addMenu("&Project")
        generate_action = QAction("&Generate Audio", self)
        generate_action.setShortcut(QKeySequence("Ctrl+Return"))
        generate_action.triggered.connect(self.start_generation)
        preview_action = QAction("Generate &30s Preview", self)
        preview_action.triggered.connect(self.start_preview)
        cancel_action = QAction("&Cancel Generation", self)
        cancel_action.triggered.connect(self.cancel_generation)
        for action in (generate_action, preview_action, cancel_action):
            project_menu.addAction(action)

        models_menu = self.menuBar().addMenu("&Models")
        manager_action = QAction("Model &Manager...", self)
        manager_action.triggered.connect(
            lambda: ModelManagerDialog(self).exec())
        models_menu.addAction(manager_action)

        settings_menu = self.menuBar().addMenu("&Settings")
        self.simple_action = QAction("&Simple Mode", self, checkable=True)
        self.simple_action.setChecked(self.settings.simple_mode)
        self.simple_action.toggled.connect(self._toggle_mode)
        updates_action = QAction("Check for &Updates...", self)
        updates_action.triggered.connect(
            lambda: CheckUpdatesDialog(self).exec())
        logs_action = QAction("Open &Logs Folder", self)
        logs_action.triggered.connect(
            lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(open_logs_folder())))
        settings_menu.addAction(self.simple_action)
        settings_menu.addAction(updates_action)
        settings_menu.addAction(logs_action)

        help_menu = self.menuBar().addMenu("&Help")
        guide_action = QAction("&User Guide", self)
        guide_action.triggered.connect(self._open_user_guide)
        about_action = QAction("&About", self)
        about_action.triggered.connect(lambda: AboutDialog(self).exec())
        help_menu.addAction(guide_action)
        help_menu.addAction(about_action)

    def _build_ui(self) -> None:
        central = QWidget()
        root_layout = QVBoxLayout(central)

        # Dashboard - two-row grid so it adapts to narrow windows
        # instead of overflowing one long horizontal strip.
        dashboard = QGridLayout()
        dashboard.setHorizontalSpacing(8)
        self.name_edit = QLineEdit(self.project.name)
        self.name_edit.setMaximumWidth(260)
        self.stat_words = QLabel("Words: 0")
        self.stat_duration = QLabel("Est. duration: -")
        self.stat_voice = QLabel("Voice: -")
        self.stat_wpm = QLabel("WPM: 155")
        for stat in (self.stat_words, self.stat_duration,
                     self.stat_voice, self.stat_wpm):
            stat.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.generate_btn = QPushButton("GENERATE AUDIO")
        self.generate_btn.setObjectName("generateBtn")
        self.generate_btn.clicked.connect(self.start_generation)
        self.preview_btn = QPushButton("30s Preview")
        self.preview_btn.clicked.connect(self.start_preview)
        dashboard.addWidget(QLabel("Project:"), 0, 0)
        dashboard.addWidget(self.name_edit, 0, 1)
        dashboard.addWidget(self.preview_btn, 0, 2)
        dashboard.addWidget(self.generate_btn, 0, 3)
        dashboard.addWidget(self.stat_words, 1, 0, 1, 2)
        dashboard.addWidget(self.stat_duration, 1, 1, Qt.AlignRight)
        dashboard.addWidget(self.stat_voice, 1, 2)
        dashboard.addWidget(self.stat_wpm, 1, 3, Qt.AlignRight)
        dashboard.setColumnStretch(1, 1)
        root_layout.addLayout(dashboard)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left: script editor
        editor_container = QWidget()
        editor_layout = QVBoxLayout(editor_container)
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_container.setMinimumWidth(280)
        self.editor = ScriptEditor()
        self.stats_row, self.stats_labels = make_stats_row()
        self.editor.text_changed_relaxed.connect(self._on_script_changed)
        self.autosave.mark_dirty()
        editor_layout.addWidget(self.editor)
        editor_layout.addWidget(self.stats_row)
        splitter.addWidget(editor_container)

        # Center: waveform + transport
        center_container = QWidget()
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_container.setMinimumWidth(240)
        self.waveform = WaveformView()
        center_layout.addWidget(self.waveform)
        transport = QHBoxLayout()
        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self._toggle_playback)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop_playback)
        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setEnabled(False)
        self.position_label = QLabel("0:00 / 0:00")
        transport.addWidget(self.play_btn)
        transport.addWidget(self.stop_btn)
        transport.addWidget(self.position_slider, 1)
        transport.addWidget(self.position_label)
        center_layout.addLayout(transport)
        splitter.addWidget(center_container)

        # Right: controls, scrollable so short/narrow windows stay usable
        self.controls = ControlsPanel()
        self.controls.settings_changed.connect(self._refresh_dashboard)
        controls_scroll = QScrollArea()
        controls_scroll.setWidget(self.controls)
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        controls_scroll.setMinimumWidth(350)
        controls_scroll.setFrameShape(QFrame.NoFrame)
        splitter.addWidget(controls_scroll)

        splitter.setStretchFactor(0, 3)   # editor grows the most
        splitter.setStretchFactor(1, 2)   # waveform
        splitter.setStretchFactor(2, 3)   # controls
        splitter.setSizes([480, 360, 400])
        root_layout.addWidget(splitter, 1)

        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self._on_player_position)
        self.player.durationChanged.connect(self._on_player_duration)
        self.player.playbackStateChanged.connect(self._on_play_state)
        self.player.errorOccurred.connect(self._on_player_error)

        self.setCentralWidget(central)
        # Responsive floor: below this size panels would cramp.
        self.setMinimumSize(1000, 620)
        self.resize(1280, 760)

    def _build_statusbar(self) -> None:
        status_widget = QWidget()
        layout = QHBoxLayout(status_widget)
        layout.setContentsMargins(4, 2, 4, 2)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximumWidth(280)
        self.status_label = QLabel(PRIVACY_NOTICE)
        pause_btn = QPushButton("Pause")
        pause_btn.clicked.connect(self.pause_generation)
        resume_btn = QPushButton("Resume")
        resume_btn.clicked.connect(self.resume_generation)
        cancel_gen_btn = QPushButton("Cancel")
        cancel_gen_btn.clicked.connect(self.cancel_generation)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.status_label, 1)
        for btn in (pause_btn, resume_btn, cancel_gen_btn):
            layout.addWidget(btn)
        self.statusBar().addPermanentWidget(status_widget, 1)
        self.status_label.setText("Ready. " + PRIVACY_NOTICE)

    def _build_autosave_timer(self) -> None:
        interval_ms = max(15, self.settings.autosave_seconds) * 1000
        self.autosave_timer = QTimer(self)
        self.autosave_timer.setInterval(interval_ms)
        self.autosave_timer.timeout.connect(self._autosave_tick)
        self.autosave_timer.start()

    # -- first run --------------------------------------------------------------

    def _first_run_check(self) -> None:
        if not self.settings.first_run_done:
            wizard = FirstRunWizard(self.settings, self)
            if wizard.exec():
                self.settings.first_run_done = True
                save_settings(self.settings)
            else:
                self.settings.first_run_done = True
        demo_path = None
        for ancestor in Path(__file__).resolve().parents[1:5]:
            candidate = ancestor / "assets" / "samples" / "the_last_train_home.txt"
            if candidate.exists():
                demo_path = candidate
                break
        if demo_path and not self.editor.toPlainText():
            try:
                text = demo_path.read_text(encoding="utf-8")
                if QMessageBox.question(
                    self, "Load sample story?",
                    "Load the demo story 'The Last Train Home'?"
                ) == QMessageBox.Yes:
                    self.editor.setPlainText(text)
            except OSError:
                pass

    # -- project management -------------------------------------------------------

    def _project_dir(self) -> Path:
        name = self.name_edit.text().strip() or "Untitled Story"
        directory = sanitize_project_path(projects_dir(), name)
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def _sync_project_object(self) -> None:
        self.project.name = self.name_edit.text().strip() or "Untitled Story"
        self.project.script_text = self.editor.toPlainText()
        self.project.settings = self.controls.collect_settings()
        self.project.app_version = VERSION
        self.project.updated_at = time.strftime("%Y-%m-%dT%H:%M:%S")

    def _new_project(self) -> None:
        self._confirm_discard()
        self.project = StoryProject()
        self.project_path = None
        self.name_edit.setText(self.project.name)
        self.editor.setPlainText("")
        self.waveform.set_audio(None)
        self.status_label.setText("New project created.")

    def _open_project(self) -> None:
        start = str(self.project_path or projects_dir())
        path, _ = QFileDialog.getOpenFileName(
            self, "Open project", start, "StoryVoice Project (*.storyproj)")
        if not path:
            return
        if has_recovery_snapshot(path) and QMessageBox.question(
            self, "Recover unsaved changes?",
            "A newer autosave snapshot exists for this project.\n"
            "Restore it?"
        ) == QMessageBox.Yes:
            recover(path)
        else:
            discard_snapshot(path)
        try:
            self.project = load_project(path)
        except Exception as error:  # noqa: BLE001
            raise UserFacingError(
                what="Could not open this project.",
                why=str(error),
                actions=["Check that the .storyproj file is valid."],
            )
        self.project_path = Path(path)
        self.name_edit.setText(self.project.name)
        self.editor.setPlainText(self.project.script_text)
        self.controls.apply_settings(self.project.settings)
        done_chunks = [c for c in self.project.chunks if c.status == "done"]
        if done_chunks and QMessageBox.question(
            self, "Resume generation?",
            f"{len(done_chunks)} chunk(s) already generated.\n"
            "Resume from the last completed chunk on next generation?"
        ) == QMessageBox.Yes:
            self.status_label.setText(
                "Resume enabled - existing chunks will be reused.")
        self.status_label.setText(f"Opened {path}")

    def _save_project(self) -> bool:
        if self.project_path is None:
            return self._save_project_as()
        self._sync_project_object()
        saved = save_project(self.project, self.project_path)
        self.status_label.setText(f"Saved {saved}")
        return True

    def _save_project_as(self) -> bool:
        default_dir = str(self._project_dir())
        path, _ = QFileDialog.getSaveFileName(
            self, "Save project as",
            str(Path(default_dir) / f"{self.project.name}.storyproj"),
            "StoryVoice Project (*.storyproj)")
        if not path:
            return False
        self._sync_project_object()
        self.project_path = save_project(self.project, path)
        discard_snapshot(path)
        self.status_label.setText(f"Saved {self.project_path}")
        return True

    def _confirm_discard(self) -> None:
        if self.autosave._dirty and self.project_path is not None:
            answer = QMessageBox.question(
                self, "Unsaved changes",
                "Save current project before continuing?")
            if answer == QMessageBox.Yes:
                self._save_project()

    def _autosave_tick(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        target = self.project_path or (
            self._project_dir() / f"{self.project.name}.storyproj"
        )
        self._sync_project_object()
        out = self.autosave.maybe_autosave(
            self.project, target, time.time())
        if out is not None:
            self.status_label.setText(f"Autosaved to {out.name}")

    # -- script editing -------------------------------------------------------------

    def _on_script_changed(self) -> None:
        self.autosave.mark_dirty()
        words = self.editor.word_count()
        wpm = int(self.controls.wpm_spin.value())
        est_minutes = words / wpm if wpm else 0
        self.stats_labels["words"].setText(f"Words: {words}")
        self.stats_labels["chars"].setText(
            f"Characters: {self.editor.character_count()}")
        minutes = int(est_minutes)
        seconds = int((est_minutes - minutes) * 60)
        self.stats_labels["duration"].setText(
            f"Est. duration: {minutes}:{seconds:02d}")
        self.stat_words.setText(f"Words: {words}")

    def _import_script(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import script", "", "Text files (*.txt *.md)")
        if path:
            self.editor.setPlainText(Path(path).read_text(encoding="utf-8"))

    def _refresh_dashboard(self) -> None:
        voice_name = self.controls.voice_combo.currentText()
        self.stat_voice.setText(f"Voice: {voice_name}")
        self.stat_wpm.setText(f"WPM: {int(self.controls.wpm_spin.value())}")
        self._on_script_changed()

    # -- generation -------------------------------------------------------------------

    def _make_options(self, preview_seconds: float = 0.0) -> GenerationOptions:
        settings = self.controls.collect_settings()
        options = GenerationOptions.from_settings(settings)
        options.preview_seconds = preview_seconds
        return options

    def _start_worker(self, preview_seconds: float = 0.0) -> None:
        if self.worker is not None and self.worker.isRunning():
            QMessageBox.information(self, "Busy",
                                    "A generation is already running.")
            return
        script_text = self.editor.toPlainText().strip()
        if not script_text:
            QMessageBox.information(self, "No script",
                                    "Write or paste a story first.")
            return
        self._sync_project_object()
        options = self._make_options(preview_seconds)
        project_dir = self._project_dir()
        self.worker = GenerationWorker(
            self.project.name, project_dir, options, script_text, parent=self)
        self.worker.existing_chunks = [
            c for c in self.project.chunks if c.status == "done"
        ] if self.project.chunks else None
        self.worker.progress_changed.connect(self._on_progress)
        self.worker.finished_ok.connect(self._on_finished)
        self.worker.failed.connect(self._on_failed)
        self.worker.cancelled.connect(self._on_cancelled)
        self.generate_btn.setEnabled(False)
        self.preview_btn.setEnabled(False)
        self.status_label.setText("Generating...")
        self.worker.start()

    def start_generation(self) -> None:
        missing = self._ensure_voice_installed()
        if missing:
            return
        self._start_worker(preview_seconds=0.0)

    def start_preview(self) -> None:
        missing = self._ensure_voice_installed()
        if missing:
            return
        self._start_worker(preview_seconds=30.0)

    def _ensure_voice_installed(self) -> bool:
        voice_id = self.controls.current_voice_id()
        from models.downloader import is_voice_installed

        if is_voice_installed(voice_id):
            return False
        answer = QMessageBox.question(
            self, "Voice not installed",
            f"'{voice_id}' must be downloaded (~60-120 MB, one time).\n\n"
            "Open the Model Manager now?")
        if answer == QMessageBox.Yes:
            ModelManagerDialog(self).exec()
        return True

    def pause_generation(self) -> None:
        if self.worker is not None:
            self.worker.pause()
            self.status_label.setText("Paused.")

    def resume_generation(self) -> None:
        if self.worker is not None:
            self.worker.resume()
            self.status_label.setText("Resumed...")

    def cancel_generation(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            self.worker.cancel()
            self.status_label.setText("Cancelling...")

    def _on_progress(self, state) -> None:
        self.progress_bar.setValue(int(state.overall_percent))
        eta = int(state.eta_seconds)
        eta_text = f" Â· ETA {eta}s" if state.phase == "voice" and eta else ""
        self.status_label.setText(
            f"[{state.phase}] {state.message}{eta_text}")

    def _on_finished(self, outcome: GenerationOutcome) -> None:
        self.generate_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        self.progress_bar.setValue(100)
        preview_only = any(i.startswith("PREVIEW") for i in outcome.quality_issues)
        audio_path = outcome.output_paths[0] if outcome.output_paths else None
        if audio_path:
            self.waveform.set_audio(str(audio_path))
            self.player.setSource(QUrl.fromLocalFile(str(audio_path)))
            self.position_slider.setEnabled(True)
        self.stats_labels["wpm_actual"].setText(
            f"Actual WPM: {outcome.actual_wpm or '-'}")
        summary = (
            f"Done: {outcome.chunk_count_done}/{outcome.chunk_count_total} "
            f"chunks Â· {outcome.duration_seconds:.1f}s Â· "
            f"{outcome.lufs} LUFS Â· TP {outcome.true_peak} dBTP"
        )
        if preview_only:
            summary = "PREVIEW ready - full render not performed."
        self.status_label.setText(summary)
        if audio_path:
            QMessageBox.information(
                self, "Generation complete",
                summary + f"\n\nOutput:\n{audio_path}"
                + ("\n\n" + COMMERCIAL_WARNING if not preview_only else ""))
        self._save_chunks_after_success(outcome)

    def _save_chunks_after_success(self, outcome: GenerationOutcome) -> None:
        """Persist chunk metadata so future runs can reuse cached audio."""
        if self.worker is None or self.worker.existing_chunks:
            pass
        try:
            from script.parser import process_script

            processed = process_script(
                self.project.script_text,
                target_wpm=self.project.settings.target_wpm,
                voice=self.project.settings.voice_id,
                words_per_chunk=self.project.settings.words_per_chunk,
                auto_emotion=self.project.settings.auto_emotion,
                emotion_intensity=self.project.settings.emotion_intensity,
            )
            cache_dir = self._project_dir() / "cache"
            by_key = {}
            for chunk in processed.chunks:
                from project.cache import chunk_cache_key
                from emotion.prosody import plan_prosody, wpm_to_length_scale
                plan = plan_prosody(chunk.emotion or "NEUTRAL", chunk.effects,
                                    chunk.pause_before, chunk.pause_after,
                                    global_intensity=
                                    self.project.settings.emotion_intensity)
                key = chunk_cache_key(
                    chunk.text, self.project.settings.voice_id, "piper",
                    round(wpm_to_length_scale(160.0, chunk.wpm_target)
                          * plan.length_scale, 5),
                    chunk.wpm_target, chunk.emotion)
                by_key[key] = chunk
            matched = 0
            for wav in cache_dir.glob("*.wav"):
                key = wav.stem
                if key in by_key:
                    chunk = by_key[key]
                    chunk.audio_path = str(wav)
                    chunk.status = "done"
                    matched += 1
            self.project.chunks = list(by_key.values())
            self._sync_project_object()
            target = self.project_path or (
                self._project_dir() / f"{self.project.name}.storyproj")
            save_project(self.project, target)
            log.info("Project saved with %d cached chunks", matched)
        except Exception:  # noqa: BLE001 - metadata persistence must not crash
            log.exception("Failed to persist chunk metadata")

    def _on_failed(self, what: str, why: str, actions: list) -> None:
        self.generate_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        self.status_label.setText(f"FAILED: {what}")
        message = what
        if why:
            message += f"\n\nWhy: {why}"
        if actions:
            message += "\n\nWhat you can do:\n" + "\n".join(
                f"- {a}" for a in actions)
        QMessageBox.critical(self, "Generation failed", message)

    def _on_cancelled(self) -> None:
        self.generate_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        self.status_label.setText(
            "Cancelled. Completed chunks are cached - next run will resume.")

    # -- playback -------------------------------------------------------------------

    def _toggle_playback(self) -> None:
        playing = QMediaPlayer.PlaybackState.PlayingState
        if self.player.playbackState() == playing:
            self.player.pause()
        elif self.player.source().isEmpty():
            QMessageBox.information(
                self, "No audio", "Generate or preview audio first.")
        else:
            self.player.play()

    def _stop_playback(self) -> None:
        self.player.stop()
        self.position_slider.setValue(0)

    def _on_play_state(self, state) -> None:
        playing = QMediaPlayer.PlaybackState.PlayingState
        self.play_btn.setText(
            "Pause" if state == playing else "Play")

    def _on_player_error(self, error, error_string: str) -> None:
        log.error("Playback error %s: %s", error, error_string)
        self.status_label.setText(f"Playback error: {error_string}")

    def _on_player_position(self, position_ms: int) -> None:
        duration = max(1, self.player.duration())
        fraction = position_ms / duration
        self.waveform.set_playhead(fraction)
        self.position_slider.blockSignals(True)
        self.position_slider.setValue(int(fraction * 1000))
        self.position_slider.blockSignals(False)
        self.position_label.setText(
            f"{_fmt_time(position_ms)} / {_fmt_time(self.player.duration())}")

    def _on_player_duration(self, duration_ms: int) -> None:
        self.position_label.setText(
            f"0:00 / {_fmt_time(duration_ms)}")

    # -- mode toggle ------------------------------------------------------------------

    def _toggle_mode(self, simple: bool) -> None:
        self.settings.simple_mode = simple
        save_settings(self.settings)
        self._set_advanced_visible(not simple)

    def _set_advanced_visible(self, visible: bool) -> None:
        self.controls.music_enabled.parentWidget().setVisible(visible)
        self.controls.loudness_combo.parentWidget().setVisible(visible)

    def _open_user_guide(self) -> None:
        guide = Path(__file__).resolve().parents[3] / "USER_GUIDE.md"
        if guide.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(guide)))
        else:
            QMessageBox.information(self, "User Guide",
                                    "USER_GUIDE.md is included in the "
                                    "repository root.")

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt naming
        if self.worker is not None and self.worker.isRunning():
            answer = QMessageBox.question(
                self, "Generation running",
                "A generation is still running. Stop it and exit?")
            if answer != QMessageBox.Yes:
                event.ignore()
                return
            self.worker.cancel()
            self.worker.wait(5000)
        self.autosave_timer.stop()
        event.accept()


def _fmt_time(ms: int) -> str:
    total_seconds = int(ms / 1000)
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"
