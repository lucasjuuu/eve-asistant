"""
Sistema de memoria con RAG (Retrieval-Augmented Generation).

- Almacena recuerdos como texto + embeddings de OpenAI.
- Persistencia local en AppData (JSON + .npy).
- Recuperación por similitud coseno.
- Nunca inventa recuerdos: solo devuelve los que existen.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from ivi.utils.paths import get_embeddings_path, get_memory_path

logger = logging.getLogger(__name__)


@dataclass
class MemoryItem:
    id: str
    text: str
    created_at: str  # ISO
    updated_at: str
    tags: list[str] = field(default_factory=list)
    importance: float = 0.5  # 0.0 - 1.0
    source: str = "user"  # user | conversation | system
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def create(
        cls,
        text: str,
        tags: list[str] | None = None,
        importance: float = 0.5,
        source: str = "user",
        metadata: dict | None = None,
    ) -> "MemoryItem":
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            id=str(uuid.uuid4()),
            text=text.strip(),
            created_at=now,
            updated_at=now,
            tags=tags or [],
            importance=max(0.0, min(1.0, importance)),
            source=source,
            metadata=metadata or {},
        )


class MemoryStore:
    """
    Almacén vectorial simple y local.
    Usa embeddings de OpenAI y búsqueda por similitud coseno.
    """

    def __init__(
        self,
        openai_client: Any | None = None,
        embedding_model: str = "text-embedding-3-small",
        enabled: bool = True,
        top_k: int = 5,
        similarity_threshold: float = 0.55,
    ):
        self.openai_client = openai_client
        self.embedding_model = embedding_model
        self.enabled = enabled
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

        self._items: list[MemoryItem] = []
        self._embeddings: np.ndarray | None = None  # shape (n, dim)
        self._load()

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def _load(self) -> None:
        mem_path = get_memory_path()
        emb_path = get_embeddings_path()

        if mem_path.exists():
            try:
                with open(mem_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                self._items = [MemoryItem(**item) for item in raw]
            except Exception as e:
                logger.error("Error cargando memoria: %s", e)
                self._items = []

        if emb_path.exists() and len(self._items) > 0:
            try:
                self._embeddings = np.load(emb_path)
                if self._embeddings.shape[0] != len(self._items):
                    logger.warning(
                        "Desajuste embeddings/items (%d vs %d). Reconstruyendo.",
                        self._embeddings.shape[0],
                        len(self._items),
                    )
                    self._embeddings = None
            except Exception as e:
                logger.error("Error cargando embeddings: %s", e)
                self._embeddings = None
        else:
            self._embeddings = None

        # Si hay items pero no embeddings, se generarán bajo demanda o al guardar.

    def _save(self) -> None:
        mem_path = get_memory_path()
        emb_path = get_embeddings_path()

        try:
            data = [asdict(item) for item in self._items]
            with open(mem_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            if self._embeddings is not None and len(self._items) > 0:
                np.save(emb_path, self._embeddings)
            elif emb_path.exists():
                emb_path.unlink(missing_ok=True)
        except Exception as e:
            logger.error("Error guardando memoria: %s", e)

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------
    def _embed(self, texts: list[str]) -> np.ndarray:
        """Genera embeddings. Requiere openai_client configurado."""
        if not self.openai_client:
            raise RuntimeError(
                "Cliente OpenAI no configurado. No se pueden generar embeddings."
            )
        if not texts:
            return np.array([])

        # OpenAI permite batch
        response = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        vectors = [item.embedding for item in response.data]
        return np.array(vectors, dtype=np.float32)

    def _ensure_embeddings(self) -> None:
        """Si faltan embeddings, los genera (costoso, solo cuando hace falta)."""
        if not self._items:
            self._embeddings = None
            return
        if self._embeddings is not None and self._embeddings.shape[0] == len(self._items):
            return
        if not self.openai_client:
            logger.warning("No hay cliente OpenAI; no se pueden generar embeddings.")
            return

        texts = [item.text for item in self._items]
        try:
            self._embeddings = self._embed(texts)
            self._save()
        except Exception as e:
            logger.error("Error generando embeddings: %s", e)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    def add(
        self,
        text: str,
        tags: list[str] | None = None,
        importance: float = 0.5,
        source: str = "user",
        metadata: dict | None = None,
    ) -> MemoryItem | None:
        if not self.enabled or not text or not text.strip():
            return None

        item = MemoryItem.create(
            text=text,
            tags=tags,
            importance=importance,
            source=source,
            metadata=metadata,
        )

        # Generar embedding individual
        try:
            if self.openai_client:
                emb = self._embed([item.text])
                if self._embeddings is None:
                    self._embeddings = emb
                else:
                    self._embeddings = np.vstack([self._embeddings, emb])
            else:
                # Sin embedding aún; se generará después
                pass
        except Exception as e:
            logger.error("No se pudo embeder el nuevo recuerdo: %s", e)

        self._items.append(item)
        self._save()
        return item

    def update(self, memory_id: str, text: str | None = None, **kwargs) -> bool:
        for i, item in enumerate(self._items):
            if item.id == memory_id:
                if text is not None:
                    item.text = text.strip()
                    # Regenerar embedding
                    if self.openai_client and self._embeddings is not None:
                        try:
                            new_emb = self._embed([item.text])
                            self._embeddings[i] = new_emb[0]
                        except Exception as e:
                            logger.error("Error actualizando embedding: %s", e)
                for k, v in kwargs.items():
                    if hasattr(item, k) and k not in ("id", "created_at"):
                        setattr(item, k, v)
                item.updated_at = datetime.now(timezone.utc).isoformat()
                self._save()
                return True
        return False

    def delete(self, memory_id: str) -> bool:
        for i, item in enumerate(self._items):
            if item.id == memory_id:
                self._items.pop(i)
                if self._embeddings is not None:
                    self._embeddings = np.delete(self._embeddings, i, axis=0)
                    if self._embeddings.shape[0] == 0:
                        self._embeddings = None
                self._save()
                return True
        return False

    def clear(self) -> None:
        self._items = []
        self._embeddings = None
        self._save()

    def list_all(self) -> list[MemoryItem]:
        return list(self._items)

    def get(self, memory_id: str) -> MemoryItem | None:
        for item in self._items:
            if item.id == memory_id:
                return item
        return None

    def count(self) -> int:
        return len(self._items)

    # ------------------------------------------------------------------
    # RAG: Retrieval
    # ------------------------------------------------------------------
    def search(
        self,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
    ) -> list[tuple[MemoryItem, float]]:
        """
        Devuelve lista de (MemoryItem, score) ordenada por similitud descendente.
        Solo incluye resultados por encima del umbral.
        """
        if not self.enabled or not query or not self._items:
            return []

        top_k = top_k or self.top_k
        threshold = threshold if threshold is not None else self.similarity_threshold

        self._ensure_embeddings()
        if self._embeddings is None or self._embeddings.shape[0] == 0:
            # Fallback: búsqueda por texto simple (sin embeddings)
            return self._keyword_fallback(query, top_k)

        try:
            query_emb = self._embed([query])
            # cosine similarity
            norms = np.linalg.norm(self._embeddings, axis=1) * np.linalg.norm(query_emb)
            # evitar división por cero
            norms = np.where(norms == 0, 1e-10, norms)
            similarities = (self._embeddings @ query_emb.T).flatten() / norms

            # ordenar
            indices = np.argsort(similarities)[::-1]

            results: list[tuple[MemoryItem, float]] = []
            for idx in indices:
                score = float(similarities[idx])
                if score < threshold:
                    break
                results.append((self._items[idx], score))
                if len(results) >= top_k:
                    break
            return results
        except Exception as e:
            logger.error("Error en búsqueda RAG: %s", e)
            return self._keyword_fallback(query, top_k)

    def _keyword_fallback(self, query: str, top_k: int) -> list[tuple[MemoryItem, float]]:
        """Búsqueda básica por palabras cuando no hay embeddings."""
        q_words = set(query.lower().split())
        scored = []
        for item in self._items:
            words = set(item.text.lower().split())
            overlap = len(q_words & words)
            if overlap > 0:
                score = overlap / max(len(q_words), 1)
                scored.append((item, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def get_relevant_context(
        self,
        query: str,
        top_k: int | None = None,
    ) -> str:
        """
        Devuelve un bloque de texto listo para inyectar en el system prompt
        o como mensaje de contexto.
        """
        results = self.search(query, top_k=top_k)
        if not results:
            return ""

        lines = ["### Recuerdos relevantes del usuario:"]
        for item, score in results:
            tags = f" [{', '.join(item.tags)}]" if item.tags else ""
            lines.append(f"- (relevancia {score:.2f}){tags}: {item.text}")
        return "\n".join(lines)

    def set_openai_client(self, client: Any) -> None:
        """Permite inyectar el cliente después de la inicialización."""
        self.openai_client = client
