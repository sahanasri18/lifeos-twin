"""Optional neural retrieval adapters.

No model is downloaded automatically. Set LIFEOS_EMBEDDINGS=sentence-transformers
and install the optional dependency to enable semantic embeddings. The default
runtime stays fully offline and deterministic.
"""
from __future__ import annotations

import os
from typing import Protocol


class Embedder(Protocol):
    def encode(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str | None = None) -> None:
        from sentence_transformers import SentenceTransformer  # optional dependency

        self.model_name = model_name or os.getenv(
            "LIFEOS_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.model = SentenceTransformer(self.model_name)

    def encode(self, texts: list[str]) -> list[list[float]]:
        vectors = self.model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()


def load_optional_embedder() -> Embedder | None:
    if os.getenv("LIFEOS_EMBEDDINGS", "off").lower() not in {"on", "sentence-transformers"}:
        return None
    try:
        return SentenceTransformerEmbedder()
    except (ImportError, OSError, RuntimeError):
        # Missing package/model/cache: keep the app usable with lexical retrieval.
        return None


class CrossEncoderReranker:
    """Optional pairwise reranker; loads only when explicitly requested."""

    def __init__(self, model_name: str | None = None) -> None:
        from sentence_transformers import CrossEncoder  # optional dependency

        self.model_name = model_name or os.getenv(
            "LIFEOS_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )
        self.model = CrossEncoder(self.model_name)

    def score(self, query: str, passages: list[str]) -> list[float]:
        pairs = [[query, passage] for passage in passages]
        return [float(value) for value in self.model.predict(pairs)]


def load_optional_reranker():
    if os.getenv("LIFEOS_RERANKER", "off").lower() not in {"on", "cross-encoder"}:
        return None
    try:
        return CrossEncoderReranker()
    except (ImportError, OSError, RuntimeError):
        return None
