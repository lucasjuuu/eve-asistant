"""Ventana principal de IVI."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ivi.ui.chat_widget import ChatWidget
from ivi.ui.memory_panel import MemoryPanel
from ivi.ui.reminders_panel import RemindersPanel
from ivi.ui.settings_dialog import SettingsDialog
from ivi.ui.styles import DARK_TECH_QSS

if TYPE_CHECKING:
    from ivi.app import IVIApp

logger = logging.getLogger(__name__)


class WorkerThread(QThread):
    """Ejecuta la llamada a la IA en segundo plano para no bloquear la UI."""
    finished_ok = Signal(str)
    finished_error = Signal(str)

    def __init__(self, conversation, text: str):
        super().__init__()
        self.conversation = conversation
        self.text = text

    def run(self):
        try:
            response = self.conversation.process_user_input(self.text)
            self.finished_ok.emit(response or "")
        except Exception as e:
            self.finished_error.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self, app: "IVIApp"):
        super().__init__()
        self.app = app
        self.setWindowTitle("IVI — Asistente de Inteligencia Artificial")
        self.resize(app.config.window_width, app.config.window_height)
        self.setStyleSheet(DARK_TECH_QSS)

        self._worker: WorkerThread | None = None
        self._build_ui()
        self._build_menu()
        self._connect_signals()
        self._update_connection_status()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # Chat (izquierda)
        self.chat = ChatWidget()
        splitter.addWidget(self.chat)

        # Paneles laterales (derecha)
        self.tabs = QTabWidget()
        self.memory_panel = MemoryPanel(self.app.memory)
        self.reminders_panel = RemindersPanel(self.app.reminders)
        self.tabs.addTab(self.memory_panel, "Memoria")
        self.tabs.addTab(self.reminders_panel, "Recordatorios")
        splitter.addWidget(self.tabs)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

    def _build_menu(self) -> None:
        menu = self.menuBar()
        file_menu = menu.addMenu("Archivo")
        settings_action = QAction("Configuración…", self)
        settings_action.triggered.connect(self.open_settings)
        file_menu.addAction(settings_action)

        clear_action = QAction("Limpiar conversación", self)
        clear_action.triggered.connect(self._clear_chat)
        file_menu.addAction(clear_action)

        file_menu.addSeparator()
        exit_action = QAction("Salir", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menu.addMenu("Ayuda")
        about_action = QAction("Acerca de IVI", self)
        about_action.triggered.connect(self._about)
        help_menu.addAction(about_action)

    def _connect_signals(self) -> None:
        self.chat.message_sent.connect(self._on_user_message)
        self.chat.mic_toggled.connect(self._on_mic_toggled)
        self.chat.stop_voice.connect(self._on_stop_voice)

        # Callbacks de estado desde los módulos
        self.app.conversation.set_status_callback(self.chat.set_status)
        self.app.conversation.set_tool_callbacks(
            on_start=self._on_tool_start,
            on_end=self._on_tool_end,
        )
        self.app.stt.set_callbacks(
            on_text=self._on_stt_text,
            on_error=self._on_stt_error,
            on_status=self.chat.set_status,
        )
        self.app.tts.set_callbacks(
            on_status=self.chat.set_status,
            on_error=lambda msg: self.chat.append_system(f"Error de voz: {msg}"),
        )
        self.app.reminders.on_reminder = self._on_reminder_fired

    def _update_connection_status(self) -> None:
        openai_ok = self.app.openai.is_configured
        eleven_ok = self.app.tts.is_configured
        self.chat.set_connection_status(openai_ok, eleven_ok)

        if not openai_ok:
            self.chat.append_system(
                "OpenAI no configurado. Ve a Archivo → Configuración e introduce tu API key."
            )

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    @Slot(str)
    def _on_user_message(self, text: str) -> None:
        self.chat.append_message("user", text)
        self.chat.set_status("pensando")
        self._worker = WorkerThread(self.app.conversation, text)
        self._worker.finished_ok.connect(self._on_ai_response)
        self._worker.finished_error.connect(self._on_ai_error)
        self._worker.start()

    @Slot(str)
    def _on_ai_response(self, response: str) -> None:
        self.chat.append_message("assistant", response)
        self.chat.set_status("inactiva")
        if self.app.config.tts_enabled and response:
            self.app.tts.speak(response)

    @Slot(str)
    def _on_ai_error(self, error: str) -> None:
        self.chat.append_system(f"Error: {error}")
        self.chat.set_status("inactiva")
        QMessageBox.warning(self, "Error de IVI", error)

    def _on_tool_start(self, name: str, args: dict) -> None:
        self.chat.append_system(f"⚙️ Ejecutando: {name}({args})")
        self.chat.set_status("pensando")

    def _on_tool_end(self, name: str, result: str) -> None:
        short = result if len(result) < 200 else result[:200] + "…"
        self.chat.append_system(f"✓ {name}: {short}")

    @Slot(bool)
    def _on_mic_toggled(self, active: bool) -> None:
        if active:
            if not self.app.config.stt_enabled:
                self.chat.append_system("El micrófono está desactivado en configuración.")
                self.chat.set_mic_active(False)
                return
            ok = self.app.stt.start_listening()
            if not ok:
                self.chat.set_mic_active(False)
        else:
            self.app.stt.stop_listening()

    @Slot(str)
    def _on_stt_text(self, text: str) -> None:
        self.chat.append_system(f"Escuchado: {text}")
        self._on_user_message(text)

    @Slot(str)
    def _on_stt_error(self, msg: str) -> None:
        self.chat.append_system(f"Error de micrófono: {msg}")
        self.chat.set_mic_active(False)

    @Slot()
    def _on_stop_voice(self) -> None:
        self.app.tts.stop()
        self.chat.set_status("inactiva")

    def _on_reminder_fired(self, reminder) -> None:
        self.chat.append_system(f"⏰ Recordatorio: {reminder.title} — {reminder.message}")
        if self.app.config.tts_enabled:
            self.app.tts.speak(f"Recordatorio: {reminder.title}. {reminder.message}")

    def open_settings(self) -> None:
        dlg = SettingsDialog(self.app.config, self)
        dlg.set_test_voice_callback(lambda: self.app.tts.test_voice())
        if dlg.exec():
            # Refresh clients
            self.app.openai.refresh()
            self.app.memory.enabled = self.app.config.memory_enabled
            self.app.memory.top_k = self.app.config.rag_top_k
            self.app.memory.similarity_threshold = self.app.config.rag_similarity_threshold
            self.app.reminders.enabled = self.app.config.reminders_enabled
            self.app.actions.set_require_confirmation(
                self.app.config.require_action_confirmation
            )
            self._update_connection_status()
            self.chat.append_system("Configuración actualizada.")

    def _clear_chat(self) -> None:
        self.app.conversation.clear_history()
        self.chat.chat_view.clear()
        self.chat.append_system("Conversación limpiada.")

    def _about(self) -> None:
        QMessageBox.about(
            self,
            "Acerca de IVI",
            "IVI — Asistente de Inteligencia Artificial\n\n"
            "Inspirado en los sistemas de Iron Man.\n"
            "Cerebro: OpenAI  |  Voz: ElevenLabs  |  Memoria: RAG local\n\n"
            "Las API keys se almacenan de forma segura en el Credential Manager de Windows.",
        )

    def closeEvent(self, event) -> None:
        self.app.shutdown()
        event.accept()
