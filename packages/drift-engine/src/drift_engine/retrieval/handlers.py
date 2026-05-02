"""Public handler functions for the ``drift.retrieval`` slice (ADR-099).

Thin delegations to ``RetrievalEngine`` and the corpus / cache helpers. This
module exposes the slice's behaviour as plain callables so that MCP tools,
CLI commands and other consumers can depend on a stable surface instead of
importing internal modules directly.
"""

from __future__ import annotations

from pathlib import Path

from drift_engine.retrieval.models import FactChunk, RetrievalResult
from drift_engine.retrieval.search import RetrievalEngine, clear_engine_cache


def retrieve(
    *,
    repo_root: Path,
    query: str,
    top_k: int = 5,
    kind: str | None = None,
    signal_id: str | None = None,
) -> list[RetrievalResult]:
    """Return BM25-ranked fact chunks for ``query`` within ``repo_root``.

    Thin delegation to ``RetrievalEngine.for_repo(repo_root).retrieve(...)``.
    """
    engine = RetrievalEngine.for_repo(repo_root)
    return engine.retrieve(query, top_k=top_k, kind=kind, signal_id=signal_id)


def cite(*, repo_root: Path, fact_id: str) -> FactChunk | None:
    """Return the full ``FactChunk`` for ``fact_id`` (migration-aware).

    Thin delegation to ``RetrievalEngine.for_repo(repo_root).cite(...)``.
    """
    engine = RetrievalEngine.for_repo(repo_root)
    return engine.cite(fact_id)


def get_engine(repo_root: Path) -> RetrievalEngine:
    """Return the cached ``RetrievalEngine`` for ``repo_root``.

    Thin delegation to ``RetrievalEngine.for_repo(repo_root)``.
    """
    return RetrievalEngine.for_repo(repo_root)


def invalidate_cache() -> None:
    """Clear the process-wide engine cache.

    Thin delegation to ``drift_engine.retrieval.search.clear_engine_cache()``.
    """
    clear_engine_cache()


__all__ = [
    "cite",
    "get_engine",
    "invalidate_cache",
    "retrieve",
]
