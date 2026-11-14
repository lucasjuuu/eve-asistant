"""
Envío de mensajes de WhatsApp a través de la cuenta del usuario.

Implementación principal: pywhatkit (abre WhatsApp Web y envía).
Requiere que el usuario tenga sesión iniciada en WhatsApp Web / el navegador
pueda abrir web.whatsapp.com.

Alternativa: control de WhatsApp Desktop con UI automation (más frágil).
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

try:
    import pywhatkit as pwk
    HAS_PYWHATKIT = True
except Exception:
    HAS_PYWHATKIT = False
    logger.warning("pywhatkit no disponible")


def _normalize_phone(phone: str) -> str:
    """
    Normaliza a formato internacional sin +.
    Ej: +54 9 11 1234-5678 → 5491112345678
    """
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("0"):
        digits = digits.lstrip("0")
    return digits


class WhatsAppController:
    def __init__(
        self,
        require_confirmation: bool = True,
        confirm_callback: Callable[[str], bool] | None = None,
    ):
        self.require_confirmation = require_confirmation
        self.confirm_callback = confirm_callback

    def _confirm(self, description: str) -> bool:
        if not self.require_confirmation:
            return True
        if self.confirm_callback:
            return bool(self.confirm_callback(description))
        logger.warning("WhatsApp requiere confirmación pero no hay callback")
        return False

    def send_message(
        self,
        phone: str,
        message: str,
        wait_time: int = 15,
        close_tab: bool = True,
    ) -> str:
        """
        Envía un mensaje de WhatsApp al número indicado.
        phone: número con código de país (ej. 5491112345678 o +54 9 11 ...)
        """
        if not HAS_PYWHATKIT:
            return (
                "pywhatkit no está instalado. Instálalo con: pip install pywhatkit\n"
                "También necesitas tener sesión abierta en WhatsApp Web."
            )

        phone_norm = _normalize_phone(phone)
        if len(phone_norm) < 10:
            return f"Número de teléfono inválido: {phone}"

        description = (
            f"Enviar WhatsApp a {phone_norm}:\n«{message[:120]}{'…' if len(message) > 120 else ''}»"
        )
        if not self._confirm(description):
            return "Envío de WhatsApp cancelado por el usuario."

        try:
            # pywhatkit abre el navegador, espera a que cargue y envía
            pwk.sendwhatmsg_instantly(
                phone_no=f"+{phone_norm}",
                message=message,
                wait_time=wait_time,
                tab_close=close_tab,
                close_time=3,
            )
            return f"Mensaje enviado a +{phone_norm} correctamente."
        except Exception as e:
            logger.exception("Error enviando WhatsApp")
            return (
                f"Error al enviar WhatsApp: {e}\n"
                "Asegúrate de tener WhatsApp Web abierto o de poder iniciar sesión, "
                "y de que el número incluya el código de país."
            )

    def send_to_contact_name(self, contact_name: str, message: str) -> str:
        """
        Intenta enviar a un contacto por nombre.
        Nota: pywhatkit trabaja principalmente con números.
        Esta función informa al modelo que necesita el número.
        """
        return (
            f"Para enviar a «{contact_name}» necesito el número de teléfono "
            f"con código de país (ej. 54911...). No puedo buscar contactos "
            f"directamente por nombre de forma fiable."
        )

    @staticmethod
    def tool_schemas() -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "send_whatsapp",
                    "description": (
                        "Envía un mensaje de WhatsApp a un número de teléfono. "
                        "El número debe incluir el código de país (ej. 5491112345678 para Argentina). "
                        "Usa esta herramienta solo cuando el usuario pida explícitamente enviar un mensaje."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "phone": {
                                "type": "string",
                                "description": "Número con código de país, sin espacios preferiblemente",
                            },
                            "message": {
                                "type": "string",
                                "description": "Texto del mensaje a enviar",
                            },
                        },
                        "required": ["phone", "message"],
                    },
                },
            },
        ]

    def dispatch(self, name: str, arguments: dict[str, Any]) -> str:
        if name == "send_whatsapp":
            return self.send_message(
                phone=arguments.get("phone", ""),
                message=arguments.get("message", ""),
            )
        return f"Herramienta WhatsApp desconocida: {name}"
