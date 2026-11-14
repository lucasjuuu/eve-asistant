"""
Control del sistema Windows: abrir aplicaciones, escribir, hacer clic,
atajos de teclado, etc.

Diseñado para ser llamado por el modelo a través de function calling.
Acciones sensibles requieren confirmación del usuario (configurable).
"""
from __future__ import annotations

import logging
import subprocess
import sys
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Dependencias opcionales
try:
    import pyautogui
    pyautogui.FAILSAFE = True          # Esquina superior izquierda aborta
    pyautogui.PAUSE = 0.15
    HAS_PYAUTOGUI = True
except Exception:
    HAS_PYAUTOGUI = False
    logger.warning("pyautogui no disponible")

try:
    import pyperclip
    HAS_PYPERCLIP = True
except Exception:
    HAS_PYPERCLIP = False


# Mapa de aplicaciones comunes en Windows
APP_COMMANDS: dict[str, list[str]] = {
    "calculadora": ["calc.exe"],
    "calculator": ["calc.exe"],
    "notepad": ["notepad.exe"],
    "bloc de notas": ["notepad.exe"],
    "explorador": ["explorer.exe"],
    "explorer": ["explorer.exe"],
    "cmd": ["cmd.exe"],
    "powershell": ["powershell.exe"],
    "paint": ["mspaint.exe"],
    "chrome": ["chrome.exe"],
    "edge": ["msedge.exe"],
    "firefox": ["firefox.exe"],
    "whatsapp": ["whatsapp.exe"],          # WhatsApp Desktop
    "spotify": ["spotify.exe"],
    "word": ["winword.exe"],
    "excel": ["excel.exe"],
    "configuración": ["ms-settings:"],
    "settings": ["ms-settings:"],
}


class ComputerController:
    """
    Ejecuta acciones de control del sistema.
    El callback de confirmación permite que la UI pida permiso al usuario.
    """

    def __init__(
        self,
        require_confirmation: bool = True,
        confirm_callback: Callable[[str], bool] | None = None,
    ):
        self.require_confirmation = require_confirmation
        self.confirm_callback = confirm_callback  # devuelve True si el usuario acepta

    def _confirm(self, description: str) -> bool:
        if not self.require_confirmation:
            return True
        if self.confirm_callback:
            return bool(self.confirm_callback(description))
        # Sin UI de confirmación → por seguridad no ejecutar
        logger.warning("Acción requiere confirmación pero no hay callback: %s", description)
        return False

    # ------------------------------------------------------------------
    # Acciones públicas (expuestas como tools)
    # ------------------------------------------------------------------
    def open_app(self, app_name: str) -> str:
        """Abre una aplicación por nombre amigable o comando."""
        key = app_name.strip().lower()
        cmd = APP_COMMANDS.get(key)

        if not cmd:
            # Intentar como ejecutable directo
            cmd = [app_name]

        description = f"Abrir aplicación: {app_name}"
        if not self._confirm(description):
            return f"Acción cancelada por el usuario: {description}"

        try:
            if sys.platform == "win32":
                # start es más robusto en Windows
                if cmd[0].startswith("ms-settings:"):
                    subprocess.Popen(["explorer", cmd[0]], shell=False)
                else:
                    subprocess.Popen(cmd, shell=False)
            else:
                subprocess.Popen(cmd)
            time.sleep(0.8)  # dar tiempo a que abra
            return f"Aplicación «{app_name}» abierta correctamente."
        except FileNotFoundError:
            return f"No se encontró la aplicación «{app_name}»."
        except Exception as e:
            logger.exception("Error abriendo app")
            return f"Error al abrir «{app_name}»: {e}"

    def type_text(self, text: str, interval: float = 0.05) -> str:
        """Escribe texto en la ventana activa (como si fuera el teclado)."""
        if not HAS_PYAUTOGUI:
            return "pyautogui no está instalado. No se puede escribir texto."

        description = f"Escribir texto: «{text[:60]}{'…' if len(text) > 60 else ''}»"
        if not self._confirm(description):
            return f"Acción cancelada: {description}"

        try:
            # Preferir portapapeles para caracteres especiales / español
            if HAS_PYPERCLIP:
                old = None
                try:
                    old = pyperclip.paste()
                except Exception:
                    pass
                pyperclip.copy(text)
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.1)
                if old is not None:
                    try:
                        pyperclip.copy(old)
                    except Exception:
                        pass
            else:
                pyautogui.write(text, interval=interval)
            return f"Texto escrito: «{text}»"
        except Exception as e:
            return f"Error al escribir: {e}"

    def press_keys(self, keys: str) -> str:
        """
        Presiona una tecla o combinación.
        Ejemplos: 'enter', 'ctrl+s', 'alt+f4', 'win+r'
        """
        if not HAS_PYAUTOGUI:
            return "pyautogui no está instalado."

        description = f"Presionar teclas: {keys}"
        if not self._confirm(description):
            return f"Acción cancelada: {description}"

        try:
            parts = [k.strip().lower() for k in keys.replace("+", " ").split()]
            # Normalizar nombres
            mapping = {
                "control": "ctrl",
                "windows": "win",
                "command": "win",
                "return": "enter",
                "escape": "esc",
            }
            parts = [mapping.get(p, p) for p in parts]

            if len(parts) == 1:
                pyautogui.press(parts[0])
            else:
                pyautogui.hotkey(*parts)
            return f"Teclas presionadas: {keys}"
        except Exception as e:
            return f"Error al presionar teclas: {e}"

    def click(self, x: int | None = None, y: int | None = None, button: str = "left") -> str:
        """Hace clic en coordenadas de pantalla o en la posición actual del ratón."""
        if not HAS_PYAUTOGUI:
            return "pyautogui no está instalado."

        if x is not None and y is not None:
            description = f"Clic {button} en ({x}, {y})"
        else:
            description = f"Clic {button} en posición actual del ratón"

        if not self._confirm(description):
            return f"Acción cancelada: {description}"

        try:
            if x is not None and y is not None:
                pyautogui.click(x, y, button=button)
            else:
                pyautogui.click(button=button)
            return f"Clic realizado ({description})"
        except Exception as e:
            return f"Error al hacer clic: {e}"

    def hotkey(self, *keys: str) -> str:
        return self.press_keys("+".join(keys))

    def open_url(self, url: str) -> str:
        """Abre una URL en el navegador predeterminado."""
        description = f"Abrir URL: {url}"
        if not self._confirm(description):
            return f"Acción cancelada: {description}"
        try:
            import webbrowser
            webbrowser.open(url)
            return f"URL abierta: {url}"
        except Exception as e:
            return f"Error al abrir URL: {e}"

    def run_shell(self, command: str) -> str:
        """
        Ejecuta un comando de shell (PowerShell en Windows).
        Solo para comandos no destructivos por defecto.
        """
        description = f"Ejecutar comando: {command}"
        if not self._confirm(description):
            return f"Acción cancelada: {description}"

        # Lista negra básica
        dangerous = ["format ", "del /s", "rm -rf", "shutdown", "rmdir /s", "Remove-Item -Recurse"]
        lower = command.lower()
        for d in dangerous:
            if d in lower:
                return f"Comando bloqueado por seguridad: contiene «{d}»"

        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", command],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    encoding="utf-8",
                    errors="replace",
                )
            else:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=30
                )
            out = (result.stdout or "").strip()
            err = (result.stderr or "").strip()
            if result.returncode != 0:
                return f"Comando terminó con código {result.returncode}.\nSalida: {out}\nError: {err}"
            return out or "Comando ejecutado correctamente (sin salida)."
        except subprocess.TimeoutExpired:
            return "El comando superó el tiempo límite (30 s)."
        except Exception as e:
            return f"Error ejecutando comando: {e}"

    def calculator_add(self, a: float, b: float) -> str:
        """
        Atajo específico: abre la Calculadora de Windows y calcula a + b.
        Útil como ejemplo de control de UI.
        """
        steps = []
        steps.append(self.open_app("calculadora"))
        time.sleep(1.2)

        # Limpiar y escribir la operación
        if HAS_PYAUTOGUI:
            # Escape por si hay algo, luego los números
            pyautogui.press("escape")
            time.sleep(0.2)
            expression = f"{a}+{b}="
            # Usar type_text interno sin volver a pedir confirmación
            old_req = self.require_confirmation
            self.require_confirmation = False
            try:
                steps.append(self.type_text(expression))
            finally:
                self.require_confirmation = old_req
        else:
            steps.append("pyautogui no disponible; solo se abrió la calculadora.")

        return " | ".join(steps)

    # ------------------------------------------------------------------
    # Descripciones para function calling
    # ------------------------------------------------------------------
    @staticmethod
    def tool_schemas() -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "open_app",
                    "description": "Abre una aplicación de Windows (calculadora, notepad, chrome, whatsapp, explorador, etc.).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "app_name": {
                                "type": "string",
                                "description": "Nombre de la aplicación (ej: calculadora, notepad, chrome, whatsapp)",
                            }
                        },
                        "required": ["app_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "type_text",
                    "description": "Escribe texto en la ventana que tiene el foco actualmente, como si el usuario escribiera en el teclado.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string", "description": "Texto a escribir"}
                        },
                        "required": ["text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "press_keys",
                    "description": "Presiona una tecla o combinación de teclas (enter, ctrl+s, alt+f4, win+r, etc.).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "keys": {
                                "type": "string",
                                "description": "Tecla o combinación, ej: 'enter', 'ctrl+c', 'alt+tab'",
                            }
                        },
                        "required": ["keys"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "open_url",
                    "description": "Abre una URL en el navegador predeterminado.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string"}
                        },
                        "required": ["url"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_shell",
                    "description": "Ejecuta un comando de PowerShell en Windows. Úsalo solo para consultas o acciones no destructivas.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"}
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calculator_add",
                    "description": "Abre la Calculadora de Windows y realiza la suma de dos números escribiéndolos.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {"type": "number"},
                            "b": {"type": "number"},
                        },
                        "required": ["a", "b"],
                    },
                },
            },
        ]

    def dispatch(self, name: str, arguments: dict[str, Any]) -> str:
        """Ejecuta la herramienta por nombre."""
        mapping = {
            "open_app": lambda: self.open_app(arguments.get("app_name", "")),
            "type_text": lambda: self.type_text(arguments.get("text", "")),
            "press_keys": lambda: self.press_keys(arguments.get("keys", "")),
            "open_url": lambda: self.open_url(arguments.get("url", "")),
            "run_shell": lambda: self.run_shell(arguments.get("command", "")),
            "calculator_add": lambda: self.calculator_add(
                float(arguments.get("a", 0)), float(arguments.get("b", 0))
            ),
        }
        fn = mapping.get(name)
        if not fn:
            return f"Herramienta desconocida: {name}"
        try:
            return fn()
        except Exception as e:
            logger.exception("Error en tool %s", name)
            return f"Error ejecutando {name}: {e}"
