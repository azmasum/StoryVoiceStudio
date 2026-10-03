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
from project.database import GenerationSettings
from tts.voices.gemini_catalog import DEFAULT_DIALOGUE, DEFAULT_NARRATOR, GEMINI_MODELS


class ControlsPanel(QWidget):
    """All generation controls in one place."""

    settings_changed = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 4, 2, 4)

        # -- Voice (Gemini cloud voices) ------------------------------------
        voice_box = QGroupBox("Voice")
        voice_form = QFormLayout(voice_box)
        self.voice_combo = QComboBox()
        self.dialogue_combo = QComboBox()
        self.voice_label = QLabel()
        self.voice_label.setWordWrap(True)
        self._reload_voices()
        self._update_voice_info()
        self.voice_combo.currentIndexChanged.connect(self._on_voice_changed)
        self.voice_combo.currentIndexChanged.connect(self.settings_changed)
        self.dialogue_combo.currentIndexChanged.connect(self.settings_changed)
        voice_form.addRow("Narrator:", self.voice_combo)
        voice_form.addRow("Dialogue:", self.dialogue_combo)
        self.dialogue_combo.setToolTip(
            "Voice for dialogue-heavy chunks. Pick a clearly different "
            "timbre (e.g. Charon + Puck) so speakers stay distinct.")
        voice_form.addRow(self.voice_label)
        self.model_combo = QComboBox()
        self.model_combo.addItems(list(GEMINI_MODELS))
        self.model_combo.setToolTip(
            "Pro: best quality. Flash: faster and cheaper.")
        self.model_combo.currentIndexChanged.connect(self.settings_changed)
        voice_form.addRow("Model:", self.model_combo)
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Gemini API key (stored locally)")
        self.api_key_edit.editingFinished.connect(self._save_api_key)
        voice_form.addRow("API key:", self.api_key_edit)
        self.usage_label = QLabel("Usage this session: -")
        self.usage_label.setWordWrap(True)
        voice_form.addRow(self.usage_label)
        self.pacing_spin = QDoubleSpinBox()
        self.pacing_spin.setRange(0.0, 30.0)
        self.pacing_spin.setValue(4.0)
        self.pacing_spin.setDecimals(0)
        self.pacing_spin.setSuffix(" s")
        self.pacing_spin.setToolTip(
            "Pause between API requests. Raise this if you hit quota "
            "errors (429) on the free tier; 0 disables pacing.")
        self.pacing_spin.valueChanged.connect(self.settings_changed)
        voice_form.addRow("API pacing:", self.pacing_spin)
        self.voice_lock = QCheckBox("Voice lock")
        self.voice_lock.setToolTip(
            "Keep the same voices consistently across all chunks.")
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

    def _update_voice_info(self) -> None:
        from tts.voices.catalog import CATALOG_VOICES

        narrator = self.current_voice_id()
        dialogue = self.current_dialogue_voice()
        notes = []
        for voice_id in (narrator, dialogue):
            for entry in CATALOG_VOICES:
                if entry["voice_id"] == voice_id:
                    notes.append(f"{voice_id} ({entry['style']})")
                    break
        self.voice_label.setText(
            "Narrator: " + (notes[0] if notes else narrator) + "\n"
            "Dialogue: " + (notes[1] if len(notes) > 1 else dialogue) + "\n"
            "Cloud voices - billed by Google per AI Studio pricing. "
            "Audio carries a SynthID watermark.")

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

    def _save_api_key(self) -> None:
        from app.config.settings import load_settings, save_settings
        from tts.manager import reset_provider

        settings = load_settings()
        settings.gemini_api_key = self.api_key_edit.text().strip()
        save_settings(settings)
        reset_provider("gemini")

    def _reload_voices(self) -> None:
        from tts.voices.catalog import CATALOG_VOICES

        for combo, default in ((self.voice_combo, DEFAULT_NARRATOR),
                               (self.dialogue_combo, DEFAULT_DIALOGUE)):
            combo.blockSignals(True)
            combo.clear()
            for entry in CATALOG_VOICES:
                combo.addItem(entry["name"], entry["voice_id"])
            index = combo.findData(default)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)

    def current_voice_id(self) -> str:
        data = self.voice_combo.currentData()
        return str(data) if data else DEFAULT_NARRATOR

    def current_dialogue_voice(self) -> str:
        data = self.dialogue_combo.currentData()
        return str(data) if data else DEFAULT_DIALOGUE

    def current_model(self) -> str:
        return self.model_combo.currentText()

    def set_usage(self, chars: int, audio_seconds: float) -> None:
        minutes = audio_seconds / 60.0
        self.usage_label.setText(
            f"Usage this session: {chars:,} chars, {minutes:.1f} min audio "
            "(billed by Google - see AI Studio billing)")

    def apply_settings(self, settings: GenerationSettings) -> None:
        index = self.voice_combo.findData(settings.voice_id)
        if index >= 0:
            self.voice_combo.setCurrentIndex(index)
        index = self.dialogue_combo.findData(
            getattr(settings, "dialogue_voice", DEFAULT_DIALOGUE))
        if index >= 0:
            self.dialogue_combo.setCurrentIndex(index)
        index = self.model_combo.findText(
            getattr(settings, "gemini_model", GEMINI_MODELS[0]))
        if index >= 0:
            self.model_combo.setCurrentIndex(index)
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
        from app.config.settings import load_settings

        self.api_key_edit.setText(load_settings().gemini_api_key)
        self.pacing_spin.setValue(float(getattr(
            settings, "api_pacing_seconds", 4.0)))

    def collect_settings(self, script_text: str = "") -> GenerationSettings:
        return GenerationSettings(
            voice_id=self.current_voice_id(),
            dialogue_voice=self.current_dialogue_voice(),
            gemini_model=self.current_model(),
            tts_engine="gemini",
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
            api_pacing_seconds=float(self.pacing_spin.value()),
        )
