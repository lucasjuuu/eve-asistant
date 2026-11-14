"""Gestión del historial de conversación y orquestación con RAG + tools."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Callable

from ivi.ai.openai_client import OpenAIClient
from ivi.config import AppConfig
from ivi.memory.store import MemoryStore
from ivi.utils.paths import get_conversation_history_path

logger = logging.getLogger(__name__)


class ConversationManager:
    def __init__(
        self,
        config: AppConfig,
        openai_client: OpenAIClient,
        memory: MemoryStore,
    ):
        self.config = config
        self.openai = openai_client
        self.memory = memory
        self.messages: list[dict] = []
        self._on_status: Callable[[str], None] | None = None
        self._on_tool_start: Callable[[str, dict], None] | None = None
        self._on_tool_end: Callable[[str, str], None] | None = None
        self._load_history()

    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        self._on_status = callback

    def set_tool_callbacks(
        self,
        on_start: Callable[[str, dict], None] | None = None,
        on_end: Callable[[str, str], None] | None = None,
    ) -> None:
        self._on_tool_start = on_start
        self._on_tool_end = on_end

    def _notify(self, status: str) -> None:
        if self._on_status:
            self._on_status(status)

    def _load_history(self) -> None:
        path = get_conversation_history_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                raw = data.get("messages", [])
                self.messages = [
                    m for m in raw
                    if m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)
                ][-self.config.max_history_messages :]
            except Exception as e:
                logger.warning("No se pudo cargar historial: %s", e)
                self.messages = []

    def save_history(self) -> None:
        path = get_conversation_history_path()
        try:
            clean = [
                m for m in self.messages
                if m.get("role") in ("user", "assistant") and m.get("content")
            ]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "messages": clean[-self.config.max_history_messages :],
                    },
                    f,
                    ensure_ascii=False,
                    indent=2,
                )
        except Exception as e:
            logger.error("Error guardando historial: %s", e)

    def clear_history(self) -> None:
        self.messages = []
        self.save_history()

    def add_user_message(self, text: str) -> None:
        self.messages.append({"role": "user", "content": text})

    def add_assistant_message(self, text: str) -> None:
        self.messages.append({"role": "assistant", "content": text})

    def process_user_input(self, text: str, auto_remember: bool = False) -> str | None:
        text = text.strip()
        if not text:
            return None

        self.add_user_message(text)
        self._notify("pensando")

        try:
            response = self.openai.chat(
                self.messages,
                user_query=text,
                stream=False,
                on_tool_start=self._on_tool_start,
                on_tool_end=self._on_tool_end,
            )
            if isinstance(response, str):
                self.add_assistant_message(response)
                self.save_history()
                if auto_remember and self.memory.enabled:
                    self._maybe_auto_remember(text, response)
                return response
            return str(response)
        except Exception:
            if self.messages and self.messages[-1].get("role") == "user":
                self.messages.pop()
            raise
        finally:
            self._notify("inactiva")

    def _maybe_auto_remember(self, user_text: str, assistant_text: str) -> None:
        lower = user_text.lower()
        triggers = [
            "recuerda que", "recuerda esto", "guarda esto",
            "no olvides que", "mi nombre es", "me llamo",
            "prefiero", "odio", "me gusta",
        ]
        if any(t in lower for t in triggers):
            self.memory.add(
                text=user_text,
                tags=["auto"],
                importance=0.7,
                source="conversation",
            )

    def force_remember(self, text: str, tags: list[str] | None = None) -> None:
        if self.memory.enabled:
            self.memory.add(text=text, tags=tags or ["manual"], source="user")
