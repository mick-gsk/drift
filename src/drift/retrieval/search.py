"""Search facade binding corpus, index, and migration registry (ADR-091).

The :class:`RetrievalEngine` is the single entry point used by MCP tools
and tests. It is cached per repository root so that repeated MCP calls
in the same process share the in-memory BM25 index.
"""

from __future__ import annotations

import threading
from pathlib import Path

from drift.retrieval.cache import load_or_build
from drift.retrieval.fact_ids import MigrationRegistry
from drift.retrieval.index import BM25Index
from drift.retrieval.models import CorpusManifest, FactChunk, RetrievalResult

_DEFAULT_MIGRATION_REGISTRY_PATH = Path("decisions") / "fact_id_migrations.jsonl"
_EXCERPT_MAX_CHARS = 800

_engine_lock = threading.Lock()
_engines: dict[Path, "RetrievalEngine"] = {}


class RetrievalEngine:
    """Bind corpus, index and migration registry for a single repository."""

    def __init__(
        self,
        manifest: CorpusManifest,
        chunks: list[FactChunk],
        *,
        migrations: MigrationRegistry | None = None,
    ) -> None:
        self._manifest = manifest
        self._chunks = list(chunks)
        self._index = BM25Index(self._chunks)
        self._by_id: dict[str, FactChunk] = {chunk.fact_id: chunk for chunk in self._chunks}
        self._migrations = migrations or MigrationRegistry({})

    # ---- Lifecycle --------------------------------------------------------

    @classmethod
    def for_repo(
        cls,
        repo_root: Path,
        *,
        migration_registry_path: Path | None = None,
    ) -> RetrievalEngine:
        """Return the cached engine for ``repo_root``, building it on first use."""
        repo_root = repo_root.resolve()
        with _engine_lock:
            engine = _engines.get(repo_root)
            if engine is not None and engine._is_fresh(repo_root):
                return engine
            manifest, chunks = load_or_build(repo_root)
            registry_path = (
                migration_registry_path
                if migration_registry_path is not None
                else repo_root / _DEFAULT_MIGRATION_REGISTRY_PATH
            )
            migrations = MigrationRegistry.from_file(registry_path)
            engine = cls(manifest, chunks, migrations=migrations)
            _engines[repo_root] = engine
            return engine

    def _is_fresh(self, repo_root: Path) -> bool:
        """Cheap freshness check — manifest digest from disk vs. in-memory."""
        current_manifest, _ = load_or_build(repo_root)
        return current_manifest.corpus_sha256 == self._manifest.corpus_sha256

    # ---- Queries ----------------------------------------------------------

    @property
    def manifest(self) -> CorpusManifest:
        return self._manifest

    @property
    def chunk_count(self) -> int:
        return len(self._chunks)

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        kind: str | None = None,
        signal_id: str | None = None,
    ) -> list[RetrievalResult]:
        """Return the top ranked :class:`RetrievalResult` list for ``query``."""
        if top_k <= 0:
            return []
        allowed: frozenset[int] | None = None
        if kind is not None or signal_id is not None:
            allowed = frozenset(
                i
                for i, chunk in enumerate(self._chunks)
                if (kind is None or chunk.kind == kind)
                and (
                    signal_id is None
                    or any(tag == f"signal:{signal_id}" for tag in chunk.tags)
                )
            )
            if not allowed:
                return []
        hits = self._index.search(query, top_k=top_k, allowed_indices=allowed)
        results: list[RetrievalResult] = []
        for idx, score in hits:
            chunk = self._chunks[idx]
            results.append(
                RetrievalResult(
                    fact_id=chunk.fact_id,
                    kind=chunk.kind,
                    source_path=chunk.source_path,
                    line_range=(chunk.line_start, chunk.line_end),
                    excerpt=_truncate(chunk.text, _EXCERPT_MAX_CHARS),
                    sha256=chunk.sha256,
                    tags=chunk.tags,
                    score=score,
                )
            )
        return results

    def cite(self, fact_id: str) -> FactChunk | None:
        """Resolve a (possibly migrated) Fact-ID to its current :class:`FactChunk`."""
        resolved = self._migrations.resolve(fact_id)
        return self._by_id.get(resolved)

    def migration_target(self, fact_id: str) -> str:
        """Return the canonical current Fact-ID for ``fact_id`` (may be identity)."""
        return self._migrations.resolve(fact_id)


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    # Cut on a word boundary if possible; fall back to hard cut.
    cut = text.rfind(" ", 0, limit)
    if cut < limit // 2:
        cut = limit
    return text[:cut].rstrip() + "..."


def clear_engine_cache() -> None:
    """Drop process-local engine caches (used in tests)."""
    with _engine_lock:
        _engines.clear()
