"""Gestión segura de credenciales con keyring (Windows Credential Manager)."""
from __future__ import annotations

import keyring
from keyring.errors import KeyringError

SERVICE_NAME = "IVI-Assistant"

# Nombres de las claves que guardamos
KEY_OPENAI = "openai_api_key"
KEY_ELEVENLABS = "elevenlabs_api_key"
KEY_ELEVENLABS_VOICE = "elevenlabs_voice_id"


class CredentialManager:
    """Wrapper seguro. Nunca guarda claves en disco en texto plano."""

    @staticmethod
    def set(key_name: str, value: str) -> None:
        if not value or not value.strip():
            raise ValueError("La clave no puede estar vacía")
        try:
            keyring.set_password(SERVICE_NAME, key_name, value.strip())
        except KeyringError as e:
            raise RuntimeError(f"No se pudo guardar la credencial: {e}") from e

    @staticmethod
    def get(key_name: str) -> str | None:
        try:
            value = keyring.get_password(SERVICE_NAME, key_name)
            return value
        except KeyringError:
            return None

    @staticmethod
    def delete(key_name: str) -> None:
        try:
            keyring.delete_password(SERVICE_NAME, key_name)
        except KeyringError:
            pass

    @staticmethod
    def has(key_name: str) -> bool:
        return CredentialManager.get(key_name) is not None

    # Atajos específicos
    @staticmethod
    def set_openai_key(api_key: str) -> None:
        CredentialManager.set(KEY_OPENAI, api_key)

    @staticmethod
    def get_openai_key() -> str | None:
        return CredentialManager.get(KEY_OPENAI)

    @staticmethod
    def set_elevenlabs_key(api_key: str) -> None:
        CredentialManager.set(KEY_ELEVENLABS, api_key)

    @staticmethod
    def get_elevenlabs_key() -> str | None:
        return CredentialManager.get(KEY_ELEVENLABS)

    @staticmethod
    def set_voice_id(voice_id: str) -> None:
        CredentialManager.set(KEY_ELEVENLABS_VOICE, voice_id)

    @staticmethod
    def get_voice_id() -> str | None:
        return CredentialManager.get(KEY_ELEVENLABS_VOICE)

    @staticmethod
    def mask_key(key: str | None, visible: int = 4) -> str:
        """Muestra solo los últimos caracteres para la UI."""
        if not key:
            return "(no configurada)"
        if len(key) <= visible:
            return "*" * len(key)
        return "*" * (len(key) - visible) + key[-visible:]
