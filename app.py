"""Clase principal de la aplicación IVI."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from ivi.actions.registry import ActionRegistry
from ivi.ai.conversation import ConversationManager
from ivi.ai.openai_client import OpenAIClient
from ivi.config import AppConfig
from ivi.memory.store import MemoryStore
from ivi.reminders.manager import ReminderManager
from ivi.ui.main_window import MainWindow
from ivi.utils.paths import get_logs_dir
from ivi.voice.stt import SpeechToText
from ivi.voice.tts import TextToSpeech

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    log_dir = get_logs_dir()
    log_file = log_dir / "ivi.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


class IVIApp:
    def __init__(self):
        setup_logging()
        logger.info("Iniciando IVI…")

        self.config = AppConfig.load()

        # Memoria con RAG
        self.memory = MemoryStore(
            openai_client=None,
            embedding_model=self.config.embedding_model,
            enabled=self.config.memory_enabled,
            top_k=self.config.rag_top_k,
            similarity_threshold=self.config.rag_similarity_threshold,
        )

        # Acciones del sistema (control PC + WhatsApp)
        self.actions = ActionRegistry(
            require_confirmation=self.config.require_action_confirmation,
            confirm_callback=None,
        )

        # Cerebro
        self.openai = OpenAIClient(
            self.config,
            self.memory,
            action_registry=self.actions,
        )
        self.memory.set_openai_client(self.openai._client)

        self.conversation = ConversationManager(
            self.config, self.openai, self.memory
        )

        # Voz
        self.stt = SpeechToText(language="es-ES")
        self.tts = TextToSpeech(self.config)

        # Recordatorios
        self.reminders = ReminderManager(
            enabled=self.config.reminders_enabled,
            check_interval=self.config.check_interval_seconds,
        )
        self.reminders.start()

        # UI
        self.qt_app = QApplication.instance() or QApplication(sys.argv)
        self.qt_app.setApplicationName("IVI")
        self.qt_app.setOrganizationName("IVI")
        self.window = MainWindow(self)

        # Conectar confirmación de acciones a la UI
        self.actions.set_confirm_callback(self._confirm_action)

    def _confirm_action(self, description: str) -> bool:
        """Muestra un diálogo de confirmación para acciones del sistema."""
        reply = QMessageBox.question(
            self.window,
            "IVI — Confirmar acción",
            f"IVI quiere realizar la siguiente acción:\n\n{description}\n\n¿Permitir?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        return reply == QMessageBox.Yes

    def run(self) -> int:
        self.window.show()
        if self.openai.is_configured:
            msg = "Sistema en línea."
            if self.memory.enabled:
                msg += " Memoria RAG activa."
            if self.config.actions_enabled:
                msg += " Control del sistema y WhatsApp disponibles."
            self.window.chat.append_system(msg)
        else:
            self.window.chat.append_system(
                "Bienvenido. Configura tu API key de OpenAI en Archivo → Configuración para comenzar."
            )
        return self.qt_app.exec()

    def shutdown(self) -> None:
        logger.info("Cerrando IVI…")
        self.stt.stop_listening()
        self.tts.stop()
        self.reminders.stop()
        self.conversation.save_history()
        self.config.save()
