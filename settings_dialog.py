"""Diálogo de configuración (API keys, modelo, voz, etc.)."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from ivi.config import AppConfig
from ivi.security import CredentialManager


class SettingsDialog(QDialog):
    def __init__(self, config: AppConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Configuración — IVI")
        self.setMinimumWidth(520)
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # --- OpenAI ---
        openai_group = QGroupBox("OpenAI")
        form = QFormLayout(openai_group)

        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setEchoMode(QLineEdit.Password)
        self.openai_key_edit.setPlaceholderText("sk-… (se guarda de forma segura)")
        form.addRow("API Key:", self.openai_key_edit)

        self.openai_masked = QLabel()
        form.addRow("Clave actual:", self.openai_masked)

        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4.1-mini",
            "gpt-4.1",
            "o4-mini",
            "gpt-3.5-turbo",
        ])
        form.addRow("Modelo:", self.model_combo)

        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        form.addRow("Temperatura:", self.temp_spin)

        layout.addWidget(openai_group)

        # --- ElevenLabs ---
        eleven_group = QGroupBox("ElevenLabs (voz)")
        form2 = QFormLayout(eleven_group)

        self.eleven_key_edit = QLineEdit()
        self.eleven_key_edit.setEchoMode(QLineEdit.Password)
        self.eleven_key_edit.setPlaceholderText("API key de ElevenLabs")
        form2.addRow("API Key:", self.eleven_key_edit)

        self.eleven_masked = QLabel()
        form2.addRow("Clave actual:", self.eleven_masked)

        self.voice_id_edit = QLineEdit()
        self.voice_id_edit.setPlaceholderText("ID de voz (ej. 21m00Tcm4TlvDq8ikWAM)")
        form2.addRow("Voice ID:", self.voice_id_edit)

        self.tts_enabled = QCheckBox("Activar respuestas habladas")
        form2.addRow(self.tts_enabled)

        test_btn = QPushButton("Probar voz")
        test_btn.clicked.connect(self._test_voice)
        form2.addRow(test_btn)

        layout.addWidget(eleven_group)

        # --- Memoria / RAG ---
        mem_group = QGroupBox("Memoria (RAG)")
        form3 = QFormLayout(mem_group)
        self.memory_enabled = QCheckBox("Activar memoria persistente + RAG")
        form3.addRow(self.memory_enabled)

        self.rag_k = QSpinBox()
        self.rag_k.setRange(1, 15)
        form3.addRow("Recuerdos a recuperar (top-k):", self.rag_k)

        self.rag_threshold = QDoubleSpinBox()
        self.rag_threshold.setRange(0.0, 1.0)
        self.rag_threshold.setSingleStep(0.05)
        form3.addRow("Umbral de similitud:", self.rag_threshold)

        layout.addWidget(mem_group)

        # --- Otros ---
        other = QGroupBox("General")
        form4 = QFormLayout(other)
        self.stt_enabled = QCheckBox("Activar entrada por micrófono")
        form4.addRow(self.stt_enabled)
        self.reminders_enabled = QCheckBox("Activar recordatorios")
        form4.addRow(self.reminders_enabled)
        self.actions_enabled = QCheckBox("Activar control del sistema y WhatsApp")
        form4.addRow(self.actions_enabled)
        self.require_confirm = QCheckBox("Pedir confirmación antes de cada acción")
        form4.addRow(self.require_confirm)
        layout.addWidget(other)

        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._test_voice_callback = None

    def set_test_voice_callback(self, cb) -> None:
        self._test_voice_callback = cb

    def _load_values(self) -> None:
        openai_key = CredentialManager.get_openai_key()
        self.openai_masked.setText(CredentialManager.mask_key(openai_key))
        self.openai_key_edit.clear()

        eleven_key = CredentialManager.get_elevenlabs_key()
        self.eleven_masked.setText(CredentialManager.mask_key(eleven_key))
        self.eleven_key_edit.clear()

        voice_id = CredentialManager.get_voice_id()
        self.voice_id_edit.setText(voice_id or "")

        idx = self.model_combo.findText(self.config.openai_model)
        if idx >= 0:
            self.model_combo.setCurrentIndex(idx)
        self.temp_spin.setValue(self.config.openai_temperature)
        self.tts_enabled.setChecked(self.config.tts_enabled)
        self.memory_enabled.setChecked(self.config.memory_enabled)
        self.rag_k.setValue(self.config.rag_top_k)
        self.rag_threshold.setValue(self.config.rag_similarity_threshold)
        self.stt_enabled.setChecked(self.config.stt_enabled)
        self.reminders_enabled.setChecked(self.config.reminders_enabled)
        self.actions_enabled.setChecked(self.config.actions_enabled)
        self.require_confirm.setChecked(self.config.require_action_confirmation)

    def _save(self) -> None:
        # Guardar claves solo si el usuario escribió algo nuevo
        new_openai = self.openai_key_edit.text().strip()
        if new_openai:
            try:
                CredentialManager.set_openai_key(new_openai)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar la clave OpenAI:\n{e}")
                return

        new_eleven = self.eleven_key_edit.text().strip()
        if new_eleven:
            try:
                CredentialManager.set_elevenlabs_key(new_eleven)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"No se pudo guardar la clave ElevenLabs:\n{e}")
                return

        voice_id = self.voice_id_edit.text().strip()
        if voice_id:
            CredentialManager.set_voice_id(voice_id)

        # Preferencias no sensibles
        self.config.openai_model = self.model_combo.currentText()
        self.config.openai_temperature = self.temp_spin.value()
        self.config.tts_enabled = self.tts_enabled.isChecked()
        self.config.memory_enabled = self.memory_enabled.isChecked()
        self.config.rag_top_k = self.rag_k.value()
        self.config.rag_similarity_threshold = self.rag_threshold.value()
        self.config.stt_enabled = self.stt_enabled.isChecked()
        self.config.reminders_enabled = self.reminders_enabled.isChecked()
        self.config.actions_enabled = self.actions_enabled.isChecked()
        self.config.require_action_confirmation = self.require_confirm.isChecked()
        self.config.save()

        self.accept()

    def _test_voice(self) -> None:
        # Guardar temporalmente si hay datos nuevos
        voice_id = self.voice_id_edit.text().strip()
        if voice_id:
            CredentialManager.set_voice_id(voice_id)
        new_eleven = self.eleven_key_edit.text().strip()
        if new_eleven:
            CredentialManager.set_elevenlabs_key(new_eleven)
        if self._test_voice_callback:
            self._test_voice_callback()
