"""Text-to-Speech con ElevenLabs."""
from __future__ import annotations

import io
import logging
import tempfile
import threading
from pathlib import Path
from typing import Callable

import requests

from ivi.config import AppConfig
from ivi.security import CredentialManager

logger = logging.getLogger(__name__)

# Intentamos usar pygame o playsound; pygame es más confiable en Windows
try:
    import pygame

    pygame.mixer.init()
    HAS_PYGAME = True
except Exception:
    HAS_PYGAME = False
    logger.warning("pygame no disponible; se usará fallback de audio.")


class TextToSpeech:
    def __init__(self, config: AppConfig):
        self.config = config
        self._playing = False
        self._stop_flag = threading.Event()
        self._thread: threading.Thread | None = None
        self._status_callback: Callable[[str], None] | None = None
        self._error_callback: Callable[[str], None] | None = None

    def set_callbacks(
        self,
        on_status: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self._status_callback = on_status
        self._error_callback = on_error

    def _notify_status(self, status: str) -> None:
        if self._status_callback:
            self._status_callback(status)

    @property
    def is_configured(self) -> bool:
        return bool(CredentialManager.get_elevenlabs_key())

    @property
    def voice_id(self) -> str | None:
        return CredentialManager.get_voice_id()

    def speak(self, text: str, blocking: bool = False) -> None:
        if not self.config.tts_enabled or not text.strip():
            return
        if not self.is_configured:
            logger.warning("ElevenLabs no configurado; se omite TTS.")
            return

        if blocking:
            self._speak_sync(text)
        else:
            self.stop()
            self._stop_flag.clear()
            self._thread = threading.Thread(
                target=self._speak_sync, args=(text,), daemon=True
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop_flag.set()
        if HAS_PYGAME:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self._playing = False
        self._notify_status("inactiva")

    def _speak_sync(self, text: str) -> None:
        api_key = CredentialManager.get_elevenlabs_key()
        voice_id = CredentialManager.get_voice_id() or "21m00Tcm4TlvDq8ikWAM"  # Rachel default

        if not api_key:
            return

        self._playing = True
        self._notify_status("hablando")

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": api_key,
        }
        payload = {
            "text": text,
            "model_id": self.config.elevenlabs_model,
            "voice_settings": {
                "stability": self.config.voice_stability,
                "similarity_boost": self.config.voice_similarity_boost,
            },
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=60)
            if resp.status_code != 200:
                msg = f"ElevenLabs error {resp.status_code}: {resp.text[:200]}"
                logger.error(msg)
                if self._error_callback:
                    self._error_callback(msg)
                return

            audio_data = resp.content
            self._play_audio(audio_data)
        except Exception as e:
            logger.exception("Error en TTS")
            if self._error_callback:
                self._error_callback(str(e))
        finally:
            self._playing = False
            self._notify_status("inactiva")

    def _play_audio(self, audio_data: bytes) -> None:
        if self._stop_flag.is_set():
            return

        if HAS_PYGAME:
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                    tmp.write(audio_data)
                    tmp_path = tmp.name
                pygame.mixer.music.load(tmp_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy() and not self._stop_flag.is_set():
                    pygame.time.wait(100)
                pygame.mixer.music.stop()
                Path(tmp_path).unlink(missing_ok=True)
                return
            except Exception as e:
                logger.warning("pygame falló: %s", e)

        # Fallback: guardar y abrir con sistema (menos ideal)
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                tmp.write(audio_data)
                tmp_path = tmp.name
            import subprocess, sys
            if sys.platform == "win32":
                subprocess.Popen(
                    ["powershell", "-c", f'(New-Object Media.SoundPlayer "{tmp_path}").PlaySync()'],
                    shell=False,
                )
            else:
                subprocess.Popen(["xdg-open", tmp_path])
        except Exception as e:
            logger.error("No se pudo reproducir audio: %s", e)

    def test_voice(self, sample_text: str = "Hola Señor, soy IVI. Sistema operativo y lista.") -> None:
        self.speak(sample_text, blocking=False)

    @property
    def is_playing(self) -> bool:
        return self._playing
