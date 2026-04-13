"""Structural protocols for dependency inversion in Drift.

Defines Protocol classes so that stable, high-fan-in modules can depend
on lightweight interfaces rather than on volatile implementation modules.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:

    import numpy as np


@runtime_checkable
class EmbeddingServiceProtocol(Protocol):
    """Minimal interface expected by signal infrastructure for embeddings."""

    def embed_text(self, text: str) -> np.ndarray | None: ...

    def embed_texts(self, texts: list[str]) -> list[np.ndarray | None]: ...

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float: ...

    @staticmethod
    def build_index(vectors: list[np.ndarray] | np.ndarray) -> object | None: ...

    @staticmethod
    def search_index(
        index: object,
        query: np.ndarray,
        top_k: int = 10,
    ) -> list[tuple[int, float]]: ...
