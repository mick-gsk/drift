"""Drift Retrieval — deterministic fact-grounding for coding agents.

See `docs/decisions/ADR-091-drift-retrieval-rag.md` for the authoritative
specification. This package indexes drift's own verified fact sources
(POLICY, ROADMAP, ADRs, audit artefacts, signal docstrings, benchmark
evidence) and exposes them via two MCP tools (`drift_retrieve`,
`drift_cite`) so agents can ground claims in citable sources instead of
free-associating.

The retrieval layer lives **outside** the detection pipeline
(ingestion -> signals -> scoring -> output) and never mutates findings,
ArchGraph, or scoring inputs. It is read-only and deterministic.
"""

from drift.retrieval.corpus_builder import build_corpus
from drift.retrieval.fact_ids import (
    MigrationRegistry,
    generate_adr_id,
    generate_audit_id,
    generate_evidence_id,
    generate_policy_id,
    generate_signal_id,
)
from drift.retrieval.handlers import cite, get_engine, invalidate_cache, retrieve
from drift.retrieval.index import BM25Index, tokenize
from drift.retrieval.models import (
    CorpusManifest,
    FactChunk,
    RetrievalResult,
    SourceEntry,
)
from drift.retrieval.search import RetrievalEngine, clear_engine_cache

__all__ = [
    "BM25Index",
    "CorpusManifest",
    "FactChunk",
    "MigrationRegistry",
    "RetrievalEngine",
    "RetrievalResult",
    "SourceEntry",
    "build_corpus",
    "cite",
    "clear_engine_cache",
    "generate_adr_id",
    "generate_audit_id",
    "generate_evidence_id",
    "generate_policy_id",
    "generate_signal_id",
    "get_engine",
    "invalidate_cache",
    "retrieve",
    "tokenize",
]
