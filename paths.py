"""Rutas de datos de la aplicación IVI en Windows (y fallbacks)."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def get_app_data_dir() -> Path:
    """Devuelve la carpeta de datos persistentes del usuario."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = Path(base) / "IVI"
    else:
        # Desarrollo / Linux / macOS
        path = Path.home() / ".ivi"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_config_path() -> Path:
    return get_app_data_dir() / "config.json"


def get_memory_path() -> Path:
    return get_app_data_dir() / "memory.json"


def get_embeddings_path() -> Path:
    return get_app_data_dir() / "memory_embeddings.npy"


def get_reminders_path() -> Path:
    return get_app_data_dir() / "reminders.json"


def get_conversation_history_path() -> Path:
    return get_app_data_dir() / "conversation_history.json"


def get_logs_dir() -> Path:
    path = get_app_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path
