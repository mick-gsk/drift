"""Bounded-context router for retrieval MCP tool implementations (ADR-091).

Covers: retrieve, cite. Binds ``RetrievalEngine`` to the FastMCP tools.
"""

from __future__ import annotations

import json
from pathlib import Path

from drift.retrieval.search import RetrievalEngine


def _error(message: str, code: str) -> str:
    return json.dumps({"error": message, "error_code": code})


async def run_retrieve(
    *,
    path: str,
    query: str,
    top_k: int,
    kind: str | None,
    signal_id: str | None,
) -> str:
    """Return BM25-ranked fact chunks as JSON for MCP consumption."""
    if not query.strip():
        return _error("query must not be empty", "DRIFT-RAG-001")
    if top_k <= 0:
        return _error("top_k must be >= 1", "DRIFT-RAG-002")
    allowed_kinds = {"policy", "roadmap", "adr", "audit", "signal", "evidence"}
    if kind is not None and kind not in allowed_kinds:
        return _error(
            f"kind must be one of {sorted(allowed_kinds)} or null",
            "DRIFT-RAG-003",
        )
    repo_root = Path(path).resolve()
    if not repo_root.exists():
        return _error(f"path not found: {path}", "DRIFT-RAG-004")

    engine = RetrievalEngine.for_repo(repo_root)
    hits = engine.retrieve(query, top_k=top_k, kind=kind, signal_id=signal_id)
    payload = {
        "corpus_sha256": engine.manifest.corpus_sha256,
        "chunk_count": engine.chunk_count,
        "query": query,
        "results": [
            {
                "fact_id": h.fact_id,
                "kind": h.kind,
                "source_path": h.source_path,
                "line_range": list(h.line_range),
                "excerpt": h.excerpt,
                "sha256": h.sha256,
                "tags": list(h.tags),
                "score": h.score,
            }
            for h in hits
        ],
        "agent_instruction": (
            "Cite at least one fact_id verbatim in your response. "
            "Call drift_cite(fact_id) to retrieve the exact verifiable text."
        ),
    }
    return json.dumps(payload, ensure_ascii=False)


async def run_cite(*, path: str, fact_id: str) -> str:
    """Expand a Fact-ID to the full chunk (migration-aware) as JSON."""
    if not fact_id.strip():
        return _error("fact_id must not be empty", "DRIFT-RAG-005")
    repo_root = Path(path).resolve()
    if not repo_root.exists():
        return _error(f"path not found: {path}", "DRIFT-RAG-004")

    engine = RetrievalEngine.for_repo(repo_root)
    resolved_id = engine.migration_target(fact_id)
    chunk = engine.cite(fact_id)
    if chunk is None:
        return _error(
            (
                f"fact_id not found: {fact_id!r} "
                f"(resolved to {resolved_id!r} via migration registry)"
            ),
            "DRIFT-RAG-006",
        )
    payload = {
        "fact_id": chunk.fact_id,
        "requested_fact_id": fact_id,
        "migrated": resolved_id != fact_id,
        "kind": chunk.kind,
        "source_path": chunk.source_path,
        "line_range": [chunk.line_start, chunk.line_end],
        "text": chunk.text,
        "sha256": chunk.sha256,
        "tags": list(chunk.tags),
        "corpus_sha256": engine.manifest.corpus_sha256,
    }
    return json.dumps(payload, ensure_ascii=False)
