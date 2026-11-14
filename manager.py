"""Sistema de recordatorios persistentes."""
from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Callable

from ivi.utils.paths import get_reminders_path

logger = logging.getLogger(__name__)

try:
    from win10toast import ToastNotifier
    HAS_TOAST = True
except Exception:
    HAS_TOAST = False
    try:
        from plyer import notification as plyer_notification
        HAS_PLYER = True
    except Exception:
        HAS_PLYER = False


@dataclass
class Reminder:
    id: str
    title: str
    message: str
    due_at: str  # ISO datetime
    created_at: str
    completed: bool = False
    notified: bool = False
    recurring: str | None = None  # daily | weekly | None

    @classmethod
    def create(
        cls,
        title: str,
        message: str,
        due_at: datetime,
        recurring: str | None = None,
    ) -> "Reminder":
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            id=str(uuid.uuid4()),
            title=title,
            message=message,
            due_at=due_at.astimezone(timezone.utc).isoformat(),
            created_at=now,
            recurring=recurring,
        )


class ReminderManager:
    def __init__(
        self,
        enabled: bool = True,
        check_interval: int = 30,
        on_reminder: Callable[[Reminder], None] | None = None,
    ):
        self.enabled = enabled
        self.check_interval = check_interval
        self.on_reminder = on_reminder
        self._reminders: list[Reminder] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._load()

    def _load(self) -> None:
        path = get_reminders_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._reminders = [Reminder(**r) for r in data]
            except Exception as e:
                logger.error("Error cargando recordatorios: %s", e)
                self._reminders = []

    def _save(self) -> None:
        path = get_reminders_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump([asdict(r) for r in self._reminders], f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("Error guardando recordatorios: %s", e)

    def add(self, title: str, message: str, due_at: datetime, recurring: str | None = None) -> Reminder:
        rem = Reminder.create(title, message, due_at, recurring)
        self._reminders.append(rem)
        self._save()
        return rem

    def delete(self, reminder_id: str) -> bool:
        for i, r in enumerate(self._reminders):
            if r.id == reminder_id:
                self._reminders.pop(i)
                self._save()
                return True
        return False

    def mark_completed(self, reminder_id: str) -> bool:
        for r in self._reminders:
            if r.id == reminder_id:
                r.completed = True
                self._save()
                return True
        return False

    def list_pending(self) -> list[Reminder]:
        return [r for r in self._reminders if not r.completed]

    def list_all(self) -> list[Reminder]:
        return list(self._reminders)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        while not self._stop.is_set():
            if self.enabled:
                self._check()
            self._stop.wait(self.check_interval)

    def _check(self) -> None:
        now = datetime.now(timezone.utc)
        for r in self._reminders:
            if r.completed or r.notified:
                continue
            try:
                due = datetime.fromisoformat(r.due_at)
                if due.tzinfo is None:
                    due = due.replace(tzinfo=timezone.utc)
                if now >= due:
                    self._fire(r)
            except Exception as e:
                logger.error("Error procesando recordatorio %s: %s", r.id, e)

    def _fire(self, r: Reminder) -> None:
        r.notified = True
        self._save()
        self._show_notification(r)
        if self.on_reminder:
            try:
                self.on_reminder(r)
            except Exception:
                pass

        # Recurring simple
        if r.recurring == "daily":
            from datetime import timedelta
            new_due = datetime.fromisoformat(r.due_at) + timedelta(days=1)
            self.add(r.title, r.message, new_due, recurring="daily")
        elif r.recurring == "weekly":
            from datetime import timedelta
            new_due = datetime.fromisoformat(r.due_at) + timedelta(weeks=1)
            self.add(r.title, r.message, new_due, recurring="weekly")

    def _show_notification(self, r: Reminder) -> None:
        title = f"IVI — {r.title}"
        msg = r.message
        try:
            if HAS_TOAST:
                toaster = ToastNotifier()
                toaster.show_toast(title, msg, duration=10, threaded=True)
            elif HAS_PLYER:
                plyer_notification.notify(title=title, message=msg, app_name="IVI", timeout=10)
            else:
                logger.info("Recordatorio (sin sistema de notificación): %s — %s", title, msg)
        except Exception as e:
            logger.error("No se pudo mostrar notificación: %s", e)
