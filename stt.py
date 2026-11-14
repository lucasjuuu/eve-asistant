"""Speech-to-Text usando speech_recognition + Google (gratis) o Whisper OpenAI."""
from __future__ import annotations

import logging
import queue
import threading
from typing import Callable

import speech_recognition as sr

logger = logging.getLogger(__name__)


class SpeechToText:
    def __init__(
        self,
        language: str = "es-ES",
        energy_threshold: int = 300,
        pause_threshold: float = 0.8,
    ):
        self.language = language
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold
        self.recognizer.dynamic_energy_threshold = True

        self._microphone: sr.Microphone | None = None
        self._listening = False
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._callback: Callable[[str], None] | None = None
        self._error_callback: Callable[[str], None] | None = None
        self._status_callback: Callable[[str], None] | None = None

    def list_microphones(self) -> list[str]:
        return sr.Microphone.list_microphone_names()

    def set_callbacks(
        self,
        on_text: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        self._callback = on_text
        self._error_callback = on_error
        self._status_callback = on_status

    def _notify_status(self, status: str) -> None:
        if self._status_callback:
            self._status_callback(status)

    def start_listening(self) -> bool:
        if self._listening:
            return True
        try:
            self._microphone = sr.Microphone()
            with self._microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
        except Exception as e:
            logger.error("No se pudo inicializar el micrófono: %s", e)
            if self._error_callback:
                self._error_callback(f"Micrófono no disponible: {e}")
            return False

        self._stop_event.clear()
        self._listening = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        self._notify_status("escuchando")
        return True

    def stop_listening(self) -> None:
        self._listening = False
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._thread = None
        self._notify_status("inactiva")

    def _listen_loop(self) -> None:
        assert self._microphone is not None
        while self._listening and not self._stop_event.is_set():
            try:
                with self._microphone as source:
                    self._notify_status("escuchando")
                    audio = self.recognizer.listen(
                        source, timeout=5, phrase_time_limit=15
                    )
                self._notify_status("procesando_voz")
                try:
                    text = self.recognizer.recognize_google(
                        audio, language=self.language
                    )
                    if text and self._callback:
                        self._callback(text)
                except sr.UnknownValueError:
                    # Silencio o no entendible → ignorar
                    pass
                except sr.RequestError as e:
                    msg = f"Error del servicio de reconocimiento: {e}"
                    logger.error(msg)
                    if self._error_callback:
                        self._error_callback(msg)
            except sr.WaitTimeoutError:
                continue
            except Exception as e:
                logger.exception("Error en bucle de escucha")
                if self._error_callback:
                    self._error_callback(str(e))
                break
        self._listening = False
        self._notify_status("inactiva")

    @property
    def is_listening(self) -> bool:
        return self._listening

    def listen_once(self, timeout: float = 5.0) -> str | None:
        """Escucha una sola frase (modo no continuo)."""
        try:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.4)
                self._notify_status("escuchando")
                audio = self.recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=12
                )
            self._notify_status("procesando_voz")
            text = self.recognizer.recognize_google(audio, language=self.language)
            return text
        except Exception as e:
            logger.warning("listen_once falló: %s", e)
            return None
        finally:
            self._notify_status("inactiva")
