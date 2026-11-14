"""Registro central de herramientas (tools) para function calling."""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

from ivi.actions.computer import ComputerController
from ivi.actions.whatsapp import WhatsAppController

logger = logging.getLogger(__name__)


class ActionRegistry:
    def __init__(
        self,
        require_confirmation: bool = True,
        confirm_callback: Callable[[str], bool] | None = None,
    ):
        self.computer = ComputerController(
            require_confirmation=require_confirmation,
            confirm_callback=confirm_callback,
        )
        self.whatsapp = WhatsAppController(
            require_confirmation=require_confirmation,
            confirm_callback=confirm_callback,
        )

    def set_confirm_callback(self, callback: Callable[[str], bool] | None) -> None:
        self.computer.confirm_callback = callback
        self.whatsapp.confirm_callback = callback

    def set_require_confirmation(self, value: bool) -> None:
        self.computer.require_confirmation = value
        self.whatsapp.require_confirmation = value

    def all_schemas(self) -> list[dict[str, Any]]:
        return self.computer.tool_schemas() + self.whatsapp.tool_schemas()

    def execute(self, name: str, arguments: dict[str, Any] | str) -> str:
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments) if arguments else {}
            except json.JSONDecodeError:
                arguments = {}

        # Computadora
        computer_tools = {
            "open_app", "type_text", "press_keys", "open_url",
            "run_shell", "calculator_add",
        }
        if name in computer_tools:
            return self.computer.dispatch(name, arguments)

        # WhatsApp
        if name in {"send_whatsapp"}:
            return self.whatsapp.dispatch(name, arguments)

        return f"Herramienta no registrada: {name}"
