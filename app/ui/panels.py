"""Right-hand control panel: voice, pacing, emotion, music, mastering."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from emotion.presets import DEFAULT_PRESET, get_preset, preset_names
from models.downloader import is_voice_installed
from project.database import GenerationSettings
from tts.voices.catalog import CATALOG_VOICES


class ControlsPanel(QWidget):
    """All generation controls in one place."""

    settings_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)

        # -- Voice ----------------------------------------------------------
        voice_box = QGroupBox("Voice")
        voice_form = QFormLayout(voice_box)
        self.voice_combo = QComboBox()
        self.voice_label = QLabel()
        self.voice_label.setWordWrap(True)
        self._reload_voices()
        self._update_voice_info()
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        self.voice_combo.currentIndexChanged.connect(self.settings_changed)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._reload_voices)
        voice_form.addRow("Voices:", self.voice_combo)
        self.speaker_combo = QComboBox()
        self.speaker_combo.currentIndexChanged.connect(self.settings_changed)
        self.speaker_combo.setEnabled(False)
        voice_form.addRow("Speaker:", self.speaker_combo)
        voice_form.addRow(self.voice_label)
        voice_form.addRow(refresh_btn)
        self.voice_lock = QCheckBox("Voice lock")
        self.voice_lock.setToolTip(
            "Keep the same voice consistently across all chunks.")
        self.voice_lock.setChecked(True)
        voice_form.addRow(self.voice_lock)
        layout.addWidget(voice_box)

        # -- Storytelling preset ---------------------------------------------
        preset_box = QGroupBox("Storytelling Preset")
        preset_form = QFormLayout(preset_box)
        self.preset_combo = QComboBox()
        for name in preset_names():
            self.preset_combo.addItem(get_preset(name).label, name)
        self.preset_combo.setCurrentText(get_preset(DEFAULT_PRESET).label)
        self.preset_description = QLabel()
        self.preset_description.setWordWrap(True)
        self._update_preset_info()
        self.preset_combo.currentIndexChanged.connect(self._apply_preset)
        preset_form.addRow(self.preset_combo)
        preset_form.addRow(self.preset_description)
        layout.addWidget(preset_box)

        # -- Pacing / emotion -------------------------------------------------
        pace_box = QGroupBox("Pacing & Emotion")
        pace_form = QFormLayout(pace_box)
        self.wpm_spin = QDoubleSpinBox()
        self.wpm_spin.setRange(120, 180)
        self.wpm_spin.setValue(155)
        self.wpm_spin.setDecimals(0)
        self.wpm_spin.setSuffix(" WPM")
        self.emotion_intensity = QSlider(Qt.Horizontal)
        self.emotion_intensity.setRange(0, 100)
        self.emotion_intensity.setValue(70)
        self.auto_emotion = QCheckBox("Auto emotion")
        self.auto_emotion.setChecked(True)
        self.emotion_intensity.valueChanged.connect(self.settings_changed)
        self.wpm_spin.valueChanged.connect(self.settings_changed)
        self.auto_emotion.stateChanged.connect(self.settings_changed)
        pace_form.addRow("Speed:", self.wpm_spin)
        pace_form.addRow("Emotion:", self.emotion_intensity)
        pace_form.addRow(self.auto_emotion)
        layout.addWidget(pace_box)

        # -- Music ------------------------------------------------------------
        music_box = QGroupBox("Background Music")
        music_form = QFormLayout(music_box)
        self.music_enabled = QCheckBox("Background music")
        self.music_path = QLineEdit()
        browse = QPushButton("Browse...")
        browse.clicked.connect(self._browse_music)
        self.music_gain = QDoubleSpinBox()
        self.music_gain.setRange(-40.0, -5.0)
        self.music_gain.setValue(-18.0)
        self.music_gain.setSuffix(" dB")
        self.ducking_db = QDoubleSpinBox()
        self.ducking_db.setRange(0.0, 18.0)
        self.ducking_db.setValue(9.0)
        self.ducking_db.setSuffix(" dB")
        self.ducking_attack = QDoubleSpinBox()
        self.ducking_attack.setRange(50, 1000)
        self.ducking_attack.setValue(200)
        self.ducking_release = QDoubleSpinBox()
        self.ducking_release.setRange(100, 2000)
        self.ducking_release.setValue(300)
        self.music_enabled.toggled.connect(self.settings_changed)
        self.music_gain.valueChanged.connect(self.settings_changed)
        self.ducking_db.valueChanged.connect(self.settings_changed)
        music_form.addRow(self.music_enabled)
        music_form.addRow("Music file:", self.music_path)
        music_form.addRow(browse)
        music_form.addRow("Music level:", self.music_gain)
        music_form.addRow("Duck depth:", self.ducking_db)
        music_form.addRow("Duck attack:", self.ducking_attack)
        music_form.addRow("Duck release:", self.ducking_release)
        layout.addWidget(music_box)

        # -- Mastering / export ----------------------------------------------
        master_box = QGroupBox("Mastering & Export")
        master_form = QFormLayout(master_box)
        self.loudness_combo = QComboBox()
        self.loudness_combo.addItems(["YouTube", "Podcast", "Audiobook",
                                      "Cinematic"])
        self.format_combo = QComboBox()
        self.format_combo.addItems(["wav", "mp3", "flac"])
        self.character_combo = QComboBox()
        self.character_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.character_combo.setMinimumContentsLength(16)
        self.character_combo.addItem("Standard narration", "standard")
        self.character_combo.addItem("Meditation preset", "meditation")
        self.character_combo.addItem("Psychology explainer", "psychology")
        self.export_stems = QCheckBox("Export stems")
        self.loudness_combo.currentIndexChanged.connect(self.settings_changed)
        self.format_combo.currentIndexChanged.connect(self.settings_changed)
        self.export_stems.stateChanged.connect(self.settings_changed)
        self.character_combo.currentIndexChanged.connect(self.settings_changed)
        master_form.addRow("Character:", self.character_combo)
        master_form.addRow("Loudness:", self.loudness_combo)
        master_form.addRow("Format:", self.format_combo)
        master_form.addRow(self.export_stems)
        layout.addWidget(master_box)

        # Keep the panel narrow enough for a side column: combos must not
        # expand to their longest item's width.
        from PySide6.QtWidgets import QComboBox as _QCB
        for combo in self.findChildren(_QCB):
            combo.setSizeAdjustPolicy(
                _QCB.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(10)

        warning = QLabel(
            "âš  Before publishing monetized content, verify that your "
            "selected AI model, voice, music and SFX licenses permit "
            "commercial use."
        )
        warning.setWordWrap(True)
        warning.setStyleSheet("color: #d9a441;")
        layout.addWidget(warning)
        layout.addStretch(1)

    # -- helpers ----------------------------------------------------------------

    def _reload_voices(self) -> None:
        self.voice_combo.blockSignals(True)
        self.voice_combo.clear()
        for entry in CATALOG_VOICES:
            installed = is_voice_installed(entry["voice_id"])
            suffix = "" if installed else "  (download required)"
            self.voice_combo.addItem(entry["name"] + suffix, entry["voice_id"])
        # Append saved voice-clone modules
        from models.voice_modules import load_modules
        modules = load_modules()
        if modules:
            self.voice_combo.insertSeparator(self.voice_combo.count())
            for m in modules:
                self.voice_combo.addItem(
                    f"{m.name}  (cloned)", f"module:{m.name}")
        self.voice_combo.blockSignals(False)
        self._update_voice_info()

    def _update_voice_info(self) -> None:
        voice_id = self.current_voice_id()
        if voice_id.startswith("module:"):
            from models.voice_modules import load_modules
            name = voice_id.split(":", 1)[1]
            for m in load_modules():
                if m.name == name:
                    self.voice_label.setText(
                        f"Cloned voice module: {m.name} "
                        f"(strength {m.tau})")
                    return
            self.voice_label.setText("Cloned voice module (not found)")
            return
        for entry in CATALOG_VOICES:
            if entry["voice_id"] == voice_id:
                commercial = "YES" if entry["commercial_use"] else "NO"
                self.voice_label.setText(
                    f"{entry['gender'].capitalize()} Â· {entry['accent']} Â· "
                    f"style: {entry['style']} Â· license: {entry['license']} Â· "
                    f"commercial use: {commercial} Â· ~{entry['model_size_mb']:.0f} MB"
                )
                return
        self.voice_label.setText("")

    def _update_preset_info(self) -> None:
        key = self.preset_combo.currentData() or DEFAULT_PRESET
        preset = get_preset(key)
        self.preset_description.setText(
            f"{preset.description}\nWPM {preset.wpm} Â· pauses x"
            f"{preset.pause_scale:.2f} Â· music: {preset.music_mood}"
        )

    def _apply_preset(self) -> None:
        key = self.preset_combo.currentData() or DEFAULT_PRESET
        preset = get_preset(key)
        self.wpm_spin.setValue(preset.wpm)
        self.emotion_intensity.setValue(int(preset.emotion_intensity * 100))
        self.ducking_db.setValue(preset.ducking_db)
        self.music_gain.setValue(preset.music_gain_db)
        self.loudness_combo.setCurrentText(preset.loudness_preset)
        self._update_preset_info()
        self.settings_changed.emit()

    def _browse_music(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Select background music", "",
            "Audio (*.wav *.mp3 *.flac *.ogg *.m4a)")
        if path:
            self.music_path.setText(path)
            self.music_enabled.setChecked(True)
            self.settings_changed.emit()

    def _on_voice_changed(self) -> None:
        self._update_voice_info()
        self._reload_speakers()

    def _reload_speakers(self) -> None:
        """Populate the speaker picker for multi-speaker voices."""
        from tts.voices.catalog import get_speakers

        speakers = get_speakers(self.current_voice_id())
        self.speaker_combo.blockSignals(True)
        self.speaker_combo.clear()
        if speakers:
            for name, sid in speakers:
                self.speaker_combo.addItem(f"Speaker {sid + 1} ({name})", sid)
            self.speaker_combo.setEnabled(True)
        else:
            self.speaker_combo.setEnabled(False)
        self.speaker_combo.blockSignals(False)

    def current_speaker_id(self) -> int | None:
        data = self.speaker_combo.currentData()
        return int(data) if self.speaker_combo.isEnabled() and data is not None else None

    def current_voice_id(self) -> str:
        data = self.voice_combo.currentData()
        return str(data) if data else "en_US-lessac-medium"

    def apply_settings(self, settings: GenerationSettings) -> None:
        index = self.voice_combo.findData(settings.voice_id)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)
        self._reload_speakers()
        if settings.speaker_id is not None:
            sid = self.speaker_combo.findData(settings.speaker_id)
            if sid >= 0:
                self.speaker_combo.setCurrentIndex(sid)
        index = self.preset_combo.findData(settings.preset)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)
        self.wpm_spin.setValue(settings.target_wpm)
        self.emotion_intensity.setValue(int(settings.emotion_intensity * 100))
        self.auto_emotion.setChecked(settings.auto_emotion)
        self.music_enabled.setChecked(settings.music_enabled)
        self.music_path.setText(settings.music_path)
        self.music_gain.setValue(settings.music_gain_db)
        self.ducking_db.setValue(settings.ducking_db)
        self.ducking_attack.setValue(settings.ducking_attack_ms)
        self.ducking_release.setValue(settings.ducking_release_ms)
        self.loudness_combo.setCurrentText(settings.loudness_preset)
        self.format_combo.setCurrentText(settings.export_format)
        self.export_stems.setChecked(settings.export_stems)
        character = getattr(settings, "voice_character", "") or (
            "meditation" if getattr(settings, "meditation_preset", False)
            else "standard")
        index = self.character_combo.findData(character)
        self.character_combo.setCurrentIndex(index if index >= 0 else 0)
        # If settings had clone info, find matching module in combo
        clone_enabled = getattr(settings, "clone_enabled", False)
        clone_ref = getattr(settings, "clone_ref_path", "")
        if clone_enabled and clone_ref:
            from models.voice_modules import load_modules, module_ref_path
            from app.config.paths import voice_modules_dir
            for m in load_modules():
                m_ref = module_ref_path(m.name)
                if m_ref and str(m_ref) == clone_ref:
                    idx = self.voice_combo.findData(f"module:{m.name}")
                    if idx >= 0:
                        self.voice_combo.setCurrentIndex(idx)
                        return

    def collect_settings(self, script_text: str = "") -> GenerationSettings:
        voice_id = self.current_voice_id()
        clone_enabled = False
        clone_ref_path = ""
        if voice_id.startswith("module:"):
            from models.voice_modules import (
                load_modules, module_ref_path, module_base_voice)
            name = voice_id.split(":", 1)[1]
            for m in load_modules():
                if m.name == name:
                    break
            ref = module_ref_path(name)
            if ref:
                clone_enabled = True
                clone_ref_path = str(ref)
            voice_id = module_base_voice(name)
        return GenerationSettings(
            voice_id=voice_id,
            speaker_id=self.current_speaker_id(),
            target_wpm=int(self.wpm_spin.value()),
            preset=self.preset_combo.currentData() or DEFAULT_PRESET,
            auto_emotion=self.auto_emotion.isChecked(),
            emotion_intensity=self.emotion_intensity.value() / 100.0,
            voice_lock=self.voice_lock.isChecked(),
            music_enabled=self.music_enabled.isChecked(),
            music_path=self.music_path.text().strip(),
            music_category="",
            music_gain_db=self.music_gain.value(),
            ducking_db=self.ducking_db.value(),
            ducking_attack_ms=int(self.ducking_attack.value()),
            ducking_release_ms=int(self.ducking_release.value()),
            loudness_preset=self.loudness_combo.currentText(),
            export_format=self.format_combo.currentText(),
            export_stems=self.export_stems.isChecked(),
            voice_character=self.character_combo.currentData() or "standard",
            clone_enabled=clone_enabled,
            clone_ref_path=clone_ref_path,
        )
