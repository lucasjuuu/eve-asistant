"""Configuración de la aplicación (preferencias no sensibles)."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ivi.utils.paths import get_config_path


@dataclass
class AppConfig:
    # OpenAI
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.7
    max_history_messages: int = 20

    # Voz
    voice_enabled: bool = True
    stt_enabled: bool = True
    tts_enabled: bool = True
    elevenlabs_model: str = "eleven_multilingual_v2"
    voice_stability: float = 0.45
    voice_similarity_boost: float = 0.75

    # Memoria / RAG
    memory_enabled: bool = True
    rag_top_k: int = 5
    rag_similarity_threshold: float = 0.55
    embedding_model: str = "text-embedding-3-small"

    # Recordatorios
    reminders_enabled: bool = True
    check_interval_seconds: int = 30

    # Acciones del sistema / agente
    actions_enabled: bool = True
    require_action_confirmation: bool = True

    # UI
    theme: str = "dark_tech"
    window_width: int = 1100
    window_height: int = 750
    font_size: int = 13

    # Personalidad (system prompt base)
    system_prompt: str = (
        "Eres IVI, un asistente de inteligencia artificial personal inspirado en "
        "los sistemas de Iron Man (JARVIS/FRIDAY). Eres inteligente, seria, elegante "
        "y respetuosa. Eres leal y colaborativa. Usas humor sutil y ocasional sarcasmo. "
        "Hablas siempre en español latinoamericano natural. Puedes dirigirte al usuario "
        "como «Señor» de forma ocasional, sin exagerar. Mantienes el contexto de la "
        "conversación y respondes de manera coherente y útil. Si no sabes algo, lo "
        "reconoces con honestidad. Explicas tus decisiones cuando es relevante."
    )

    extra: dict[str, Any] = field(default_factory=dict)

    def save(self, path: Path | None = None) -> None:
        path = path or get_config_path()
        data = asdict(self)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path | None = None) -> "AppConfig":
        path = path or get_config_path()
        if not path.exists():
            cfg = cls()
            cfg.save(path)
            return cfg
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Filtrar solo campos conocidos
            known = {f.name for f in cls.__dataclass_fields__.values()}
            filtered = {k: v for k, v in data.items() if k in known}
            return cls(**filtered)
        except Exception:
            return cls()
