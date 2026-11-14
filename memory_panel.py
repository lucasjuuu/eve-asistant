"""Panel de gestión de memoria (RAG)."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ivi.memory.store import MemoryStore


class MemoryPanel(QWidget):
    memory_changed = Signal()

    def __init__(self, memory: MemoryStore, parent=None):
        super().__init__(parent)
        self.memory = memory
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Recuerdos guardados (RAG)"))

        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._on_select)
        layout.addWidget(self.list_widget, stretch=1)

        self.detail = QTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(100)
        layout.addWidget(self.detail)

        # Añadir
        add_row = QHBoxLayout()
        self.new_text = QLineEdit()
        self.new_text.setPlaceholderText("Nuevo recuerdo…")
        add_row.addWidget(self.new_text)
        add_btn = QPushButton("Añadir")
        add_btn.clicked.connect(self._add)
        add_row.addWidget(add_btn)
        layout.addLayout(add_row)

        # Acciones
        btn_row = QHBoxLayout()
        del_btn = QPushButton("Eliminar seleccionado")
        del_btn.clicked.connect(self._delete)
        btn_row.addWidget(del_btn)
        clear_btn = QPushButton("Borrar todo")
        clear_btn.clicked.connect(self._clear)
        btn_row.addWidget(clear_btn)
        refresh_btn = QPushButton("Actualizar")
        refresh_btn.clicked.connect(self.refresh)
        btn_row.addWidget(refresh_btn)
        layout.addLayout(btn_row)

        self.count_label = QLabel("0 recuerdos")
        layout.addWidget(self.count_label)

    def refresh(self) -> None:
        self.list_widget.clear()
        items = self.memory.list_all()
        for item in sorted(items, key=lambda x: x.created_at, reverse=True):
            display = item.text[:80] + ("…" if len(item.text) > 80 else "")
            lw_item = QListWidgetItem(display)
            lw_item.setData(256, item.id)  # Qt.UserRole
            self.list_widget.addItem(lw_item)
        self.count_label.setText(f"{len(items)} recuerdos")
        self.detail.clear()

    def _on_select(self) -> None:
        selected = self.list_widget.selectedItems()
        if not selected:
            self.detail.clear()
            return
        mem_id = selected[0].data(256)
        item = self.memory.get(mem_id)
        if item:
            tags = ", ".join(item.tags) if item.tags else "—"
            self.detail.setPlainText(
                f"{item.text}\n\n"
                f"Creado: {item.created_at}\n"
                f"Tags: {tags}\n"
                f"Importancia: {item.importance}\n"
                f"Fuente: {item.source}"
            )

    def _add(self) -> None:
        text = self.new_text.text().strip()
        if not text:
            return
        self.memory.add(text, tags=["manual"], source="user")
        self.new_text.clear()
        self.refresh()
        self.memory_changed.emit()

    def _delete(self) -> None:
        selected = self.list_widget.selectedItems()
        if not selected:
            return
        mem_id = selected[0].data(256)
        self.memory.delete(mem_id)
        self.refresh()
        self.memory_changed.emit()

    def _clear(self) -> None:
        reply = QMessageBox.question(
            self,
            "Confirmar",
            "¿Borrar todos los recuerdos? Esta acción no se puede deshacer.",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.memory.clear()
            self.refresh()
            self.memory_changed.emit()
