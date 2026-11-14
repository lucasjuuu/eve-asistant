"""Widget de chat principal."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class ChatWidget(QWidget):
    message_sent = Signal(str)
    mic_toggled = Signal(bool)
    stop_voice = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header / status
        header = QHBoxLayout()
        self.title_label = QLabel("IVI")
        self.title_label.setStyleSheet(
            "font-size: 20px; font-weight: 700; color: #00b4ff; letter-spacing: 3px;"
        )
        header.addWidget(self.title_label)

        self.status_label = QLabel("INACTIVA")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setProperty("status", "inactiva")
        self.status_label.setAlignment(Qt.AlignCenter)
        header.addStretch()
        header.addWidget(self.status_label)

        # Indicadores de conexión
        self.openai_status = QLabel("OpenAI: —")
        self.openai_status.setObjectName("connFail")
        self.eleven_status = QLabel("ElevenLabs: —")
        self.eleven_status.setObjectName("connFail")
        header.addWidget(self.openai_status)
        header.addWidget(self.eleven_status)
        layout.addLayout(header)

        # Historial
        self.chat_view = QTextEdit()
        self.chat_view.setReadOnly(True)
        self.chat_view.setPlaceholderText("La conversación aparecerá aquí…")
        layout.addWidget(self.chat_view, stretch=1)

        # Input row
        input_row = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Escribe un mensaje o usa el micrófono…")
        self.input_field.returnPressed.connect(self._on_send)
        input_row.addWidget(self.input_field, stretch=1)

        self.mic_btn = QPushButton("🎤")
        self.mic_btn.setObjectName("micButton")
        self.mic_btn.setCheckable(True)
        self.mic_btn.setToolTip("Activar / desactivar micrófono")
        self.mic_btn.toggled.connect(self.mic_toggled.emit)
        input_row.addWidget(self.mic_btn)

        self.stop_btn = QPushButton("⏹")
        self.stop_btn.setObjectName("stopVoiceButton")
        self.stop_btn.setToolTip("Detener voz")
        self.stop_btn.clicked.connect(self.stop_voice.emit)
        input_row.addWidget(self.stop_btn)

        self.send_btn = QPushButton("Enviar")
        self.send_btn.setObjectName("sendButton")
        self.send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self.send_btn)

        layout.addLayout(input_row)

    def _on_send(self) -> None:
        text = self.input_field.text().strip()
        if text:
            self.message_sent.emit(text)
            self.input_field.clear()

    def append_message(self, role: str, text: str) -> None:
        if role == "user":
            html = (
                f'<p style="margin:6px 0;"><span style="color:#00ccff;font-weight:600;">Tú:</span> '
                f'<span style="color:#cceeff;">{self._escape(text)}</span></p>'
            )
        else:
            html = (
                f'<p style="margin:6px 0;"><span style="color:#00ffaa;font-weight:600;">IVI:</span> '
                f'<span style="color:#e0f0ff;">{self._escape(text)}</span></p>'
            )
        self.chat_view.moveCursor(QTextCursor.End)
        self.chat_view.insertHtml(html)
        self.chat_view.moveCursor(QTextCursor.End)

    def append_system(self, text: str) -> None:
        html = (
            f'<p style="margin:4px 0;color:#8899aa;font-style:italic;">'
            f'[{self._escape(text)}]</p>'
        )
        self.chat_view.moveCursor(QTextCursor.End)
        self.chat_view.insertHtml(html)
        self.chat_view.moveCursor(QTextCursor.End)

    def set_status(self, status: str) -> None:
        mapping = {
            "inactiva": "INACTIVA",
            "escuchando": "ESCUCHANDO",
            "pensando": "PENSANDO…",
            "hablando": "HABLANDO",
            "procesando_voz": "PROCESANDO VOZ",
        }
        self.status_label.setText(mapping.get(status, status.upper()))
        self.status_label.setProperty("status", status)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)

    def set_connection_status(self, openai_ok: bool, eleven_ok: bool) -> None:
        self.openai_status.setText(f"OpenAI: {'✓' if openai_ok else '✗'}")
        self.openai_status.setObjectName("connOk" if openai_ok else "connFail")
        self.eleven_status.setText(f"ElevenLabs: {'✓' if eleven_ok else '✗'}")
        self.eleven_status.setObjectName("connOk" if eleven_ok else "connFail")
        for w in (self.openai_status, self.eleven_status):
            w.style().unpolish(w)
            w.style().polish(w)

    def set_mic_active(self, active: bool) -> None:
        self.mic_btn.blockSignals(True)
        self.mic_btn.setChecked(active)
        self.mic_btn.blockSignals(False)

    @staticmethod
    def _escape(text: str) -> str:
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace("\n", "<br>")
        )
