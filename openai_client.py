"""Cliente OpenAI con soporte de contexto + RAG + function calling (agent)."""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Generator

from openai import OpenAI, APIError, AuthenticationError, RateLimitError

from ivi.config import AppConfig
from ivi.memory.store import MemoryStore
from ivi.security import CredentialManager

logger = logging.getLogger(__name__)


class OpenAIClient:
    def __init__(
        self,
        config: AppConfig,
        memory: MemoryStore | None = None,
        action_registry: Any | None = None,
    ):
        self.config = config
        self.memory = memory
        self.action_registry = action_registry
        self._client: OpenAI | None = None
        self._rebuild_client()

    def _rebuild_client(self) -> None:
        api_key = CredentialManager.get_openai_key()
        if api_key:
            self._client = OpenAI(api_key=api_key)
            if self.memory:
                self.memory.set_openai_client(self._client)
        else:
            self._client = None

    @property
    def is_configured(self) -> bool:
        return self._client is not None

    def refresh(self) -> None:
        self._rebuild_client()

    def set_action_registry(self, registry: Any) -> None:
        self.action_registry = registry

    def chat(
        self,
        messages: list[dict[str, Any]],
        user_query: str | None = None,
        stream: bool = False,
        max_tool_rounds: int = 6,
        on_tool_start: Callable[[str, dict], None] | None = None,
        on_tool_end: Callable[[str, str], None] | None = None,
    ) -> str | Generator[str, None, None]:
        """
        Genera respuesta. Soporta:
        - RAG (inyección de recuerdos)
        - Function calling / tools (control del PC, WhatsApp, etc.)
        """
        if not self._client:
            raise RuntimeError(
                "OpenAI no está configurado. Ve a Configuración e introduce tu API key."
            )

        system_content = self.config.system_prompt

        # Instrucciones extra para el agente
        system_content += (
            "\n\nPuedes controlar la computadora del usuario y enviar mensajes de WhatsApp "
            "usando las herramientas disponibles cuando te lo pida explícitamente. "
            "Antes de acciones importantes resume qué vas a hacer. "
            "Si una herramienta falla, explica el error con claridad. "
            "No inventes resultados de herramientas: usa solo lo que devuelven."
        )

        if (
            self.memory
            and self.memory.enabled
            and user_query
            and self.config.memory_enabled
        ):
            rag_context = self.memory.get_relevant_context(
                user_query, top_k=self.config.rag_top_k
            )
            if rag_context:
                system_content += (
                    f"\n\n{rag_context}\n\n"
                    "Usa los recuerdos anteriores solo si son relevantes. "
                    "No inventes información que no esté en ellos."
                )

        # Construir mensajes con system
        full_messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_content}
        ]
        history = messages[-self.config.max_history_messages :]
        full_messages.extend(history)

        tools = None
        if self.action_registry and getattr(self.config, "actions_enabled", True):
            tools = self.action_registry.all_schemas()

        if stream and not tools:
            return self._stream_chat(full_messages)

        try:
            return self._chat_with_tools(
                full_messages,
                tools=tools,
                max_rounds=max_tool_rounds,
                on_tool_start=on_tool_start,
                on_tool_end=on_tool_end,
            )
        except AuthenticationError:
            raise RuntimeError(
                "API key de OpenAI inválida o expirada. Revisa la configuración."
            )
        except RateLimitError:
            raise RuntimeError(
                "Límite de uso de OpenAI alcanzado. Espera un momento e intenta de nuevo."
            )
        except APIError as e:
            raise RuntimeError(f"Error de la API de OpenAI: {e}") from e
        except Exception as e:
            logger.exception("Error inesperado en OpenAI")
            raise RuntimeError(f"Error al contactar OpenAI: {e}") from e

    def _chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict] | None,
        max_rounds: int = 6,
        on_tool_start: Callable | None = None,
        on_tool_end: Callable | None = None,
    ) -> str:
        current = list(messages)

        for _ in range(max_rounds):
            kwargs: dict[str, Any] = {
                "model": self.config.openai_model,
                "messages": current,
                "temperature": self.config.openai_temperature,
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            msg = choice.message

            # Si el modelo quiere llamar herramientas
            if msg.tool_calls:
                # Añadir el mensaje del assistant con tool_calls
                current.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for tc in msg.tool_calls
                        ],
                    }
                )

                for tc in msg.tool_calls:
                    name = tc.function.name
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                    except json.JSONDecodeError:
                        args = {}

                    if on_tool_start:
                        try:
                            on_tool_start(name, args)
                        except Exception:
                            pass

                    result = "Herramientas no disponibles."
                    if self.action_registry:
                        result = self.action_registry.execute(name, args)

                    if on_tool_end:
                        try:
                            on_tool_end(name, result)
                        except Exception:
                            pass

                    current.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result,
                        }
                    )
                # Continuar el bucle para que el modelo vea el resultado
                continue

            # Respuesta final de texto
            return msg.content or ""

        return "Se alcanzó el límite de pasos de herramientas. Revisa el resultado parcial."

    def _stream_chat(self, messages: list[dict]) -> Generator[str, None, None]:
        stream = self._client.chat.completions.create(
            model=self.config.openai_model,
            messages=messages,
            temperature=self.config.openai_temperature,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self._client:
            raise RuntimeError("OpenAI no configurado")
        response = self._client.embeddings.create(
            model=self.config.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]
