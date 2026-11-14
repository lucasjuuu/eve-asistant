"""Panel de recordatorios."""
from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import QDateTime, Qt
from PySide6.QtWidgets import (
    QDateTimeEdit,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ivi.reminders.manager import ReminderManager


class RemindersPanel(QWidget):
    def __init__(self, manager: ReminderManager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Recordatorios programados"))

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, stretch=1)

        # Formulario
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Título")
        layout.addWidget(self.title_edit)

        self.msg_edit = QLineEdit()
        self.msg_edit.setPlaceholderText("Mensaje")
        layout.addWidget(self.msg_edit)

        self.dt_edit = QDateTimeEdit()
        self.dt_edit.setCalendarPopup(True)
        self.dt_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.dt_edit.setDisplayFormat("dd/MM/yyyy HH:mm")
        layout.addWidget(self.dt_edit)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Añadir recordatorio")
        add_btn.clicked.connect(self._add)
        btn_row.addWidget(add_btn)
        del_btn = QPushButton("Eliminar")
        del_btn.clicked.connect(self._delete)
        btn_row.addWidget(del_btn)
        refresh_btn = QPushButton("Actualizar")
        refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(refresh_btn)
        layout.addLayout(btn_row)

        note = QLabel(
            "Nota: los recordatorios solo se notifican mientras IVI esté en ejecución. "
            "Si cierras la aplicación, se guardan pero no avisarán hasta que la vuelvas a abrir."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #8899aa; font-size: 11px;")
        layout.addWidget(note)

    def refresh(self) -> None:
        self.list_widget.clear()
        for r in self.manager.list_pending():
            try:
                due = datetime.fromisoformat(r.due_at)
                due_str = due.astimezone().strftime("%d/%m/%Y %H:%M")
            except Exception:
                due_str = r.due_at
            text = f"[{due_str}] {r.title}: {r.message}"
            item = QListWidgetItem(text)
            item.setData(256, r.id)
            self.list_widget.addItem(item)

    def _add(self) -> None:
        title = self.title_edit.text().strip() or "Recordatorio"
        msg = self.msg_edit.text().strip() or title
        qdt = self.dt_edit.dateTime()
        due = qdt.toPython()
        # Asegurar timezone aware
        if due.tzinfo is None:
            due = due.astimezone()
        self.manager.add(title, msg, due)
        self.title_edit.clear()
        self.msg_edit.clear()
        self.refresh()

    def _delete(self) -> None:
        selected = self.list_widget.selectedItems()
        if not selected:
            return
        rid = selected[0].data(256)
        self.manager.delete(rid)
        self.refresh()
