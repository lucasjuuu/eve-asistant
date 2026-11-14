"""Estilos visuales inspirados en estética tecnológica (Iron Man / HUD)."""

DARK_TECH_QSS = """
/* ===== Base ===== */
QWidget {
    background-color: #0a0e17;
    color: #e0f0ff;
    font-family: "Segoe UI", "Inter", "Roboto", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #060a12;
}

/* ===== Chat area ===== */
QTextEdit, QPlainTextEdit {
    background-color: #0d1520;
    border: 1px solid #1a3a5c;
    border-radius: 8px;
    padding: 10px;
    selection-background-color: #1e90ff;
    color: #d0e8ff;
}

QLineEdit {
    background-color: #0d1520;
    border: 1px solid #1a3a5c;
    border-radius: 6px;
    padding: 8px 12px;
    color: #e0f0ff;
}
QLineEdit:focus {
    border: 1px solid #00b4ff;
}

/* ===== Buttons ===== */
QPushButton {
    background-color: #0e2a45;
    border: 1px solid #1e90ff;
    border-radius: 6px;
    padding: 8px 16px;
    color: #a0d8ff;
    font-weight: 600;
}
QPushButton:hover {
    background-color: #143a5c;
    border-color: #00b4ff;
    color: #ffffff;
}
QPushButton:pressed {
    background-color: #0a1f35;
}
QPushButton:disabled {
    background-color: #0a1520;
    border-color: #1a2a3a;
    color: #556677;
}

QPushButton#micButton {
    background-color: #1a3a2a;
    border-color: #00cc88;
    color: #80ffcc;
    min-width: 48px;
    min-height: 48px;
    border-radius: 24px;
    font-size: 18px;
}
QPushButton#micButton:checked, QPushButton#micButton[listening="true"] {
    background-color: #cc3344;
    border-color: #ff5566;
    color: #ffffff;
}

QPushButton#sendButton {
    background-color: #003366;
    border-color: #00aaff;
}

QPushButton#stopVoiceButton {
    background-color: #3a1a1a;
    border-color: #ff5566;
    color: #ffaaaa;
}

/* ===== Status indicator ===== */
QLabel#statusLabel {
    font-weight: 700;
    letter-spacing: 1px;
    padding: 4px 12px;
    border-radius: 12px;
    background-color: #0d1a28;
    border: 1px solid #1a3a5c;
}
QLabel#statusLabel[status="inactiva"] {
    color: #6688aa;
}
QLabel#statusLabel[status="escuchando"] {
    color: #00ff99;
    border-color: #00cc77;
}
QLabel#statusLabel[status="pensando"] {
    color: #ffcc00;
    border-color: #cc9900;
}
QLabel#statusLabel[status="hablando"] {
    color: #00aaff;
    border-color: #0088cc;
}
QLabel#statusLabel[status="procesando_voz"] {
    color: #ffaa00;
}

/* ===== Side panels ===== */
QTabWidget::pane {
    border: 1px solid #1a3a5c;
    border-radius: 6px;
    background-color: #0a121c;
}
QTabBar::tab {
    background-color: #0d1a28;
    border: 1px solid #1a3a5c;
    padding: 8px 16px;
    margin-right: 2px;
    color: #88aacc;
}
QTabBar::tab:selected {
    background-color: #123050;
    color: #00b4ff;
    border-bottom-color: #00b4ff;
}

/* ===== Lists ===== */
QListWidget {
    background-color: #0d1520;
    border: 1px solid #1a3a5c;
    border-radius: 6px;
    outline: none;
}
QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #122030;
}
QListWidget::item:selected {
    background-color: #1a3a5c;
    color: #ffffff;
}

/* ===== GroupBox ===== */
QGroupBox {
    border: 1px solid #1a3a5c;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
    color: #88bbdd;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

/* ===== Scrollbars ===== */
QScrollBar:vertical {
    background: #0a121c;
    width: 10px;
    border-radius: 5px;
}
QScrollBar::handle:vertical {
    background: #1a3a5c;
    border-radius: 5px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #2a5a8c;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* ===== Labels de conexión ===== */
QLabel#connOk {
    color: #00cc88;
}
QLabel#connFail {
    color: #ff5566;
}

/* ===== Dialog ===== */
QDialog {
    background-color: #0a0e17;
}
QDialogButtonBox QPushButton {
    min-width: 90px;
}
"""
