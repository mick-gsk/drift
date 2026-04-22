"""Tests for drift.retrieval.index and search (ADR-091).

Cover:
- BM25 determinism and tie-breaking,
- kind / signal_id filters,
- RetrievalEngine round-trip (retrieve -> cite -> sha-match),
- gold-set precision@5 on hand-curated query -> fact_id pairs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from drift.retrieval.cache import clear_memory_cache
from drift.retrieval.index import BM25Index, tokenize
from drift.retrieval.models import FactChunk
from drift.retrieval.search import RetrievalEngine, clear_engine_cache


@pytest.fixture(scope="module")
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def tiny_corpus() -> list[FactChunk]:
    return [
        FactChunk(
            fact_id="POLICY#S8.p1",
            kind="policy",
            source_path="POLICY.md",
            line_start=1,
            line_end=1,
            text="Eine Aufgabe gilt als zulaessig, wenn sie ein Kriterium erfuellt.",
            sha256="a" * 64,
            tags=("section:8",),
        ),
        FactChunk(
            fact_id="POLICY#S8.p2",
            kind="policy",
            source_path="POLICY.md",
            line_start=2,
            line_end=2,
            text="Zulassungskriterium erfuellt heisst handlungsfaehig sein.",
            sha256="b" * 64,
            tags=("section:8",),
        ),
        FactChunk(
            fact_id="SIGNAL/pfs#rationale",
            kind="signal",
            source_path="src/drift/signals/pfs.py",
            line_start=1,
            line_end=1,
            text="Pattern fragmentation detection for architectural drift.",
            sha256="c" * 64,
            tags=("signal:pfs",),
        ),
    ]


# --- BM25 primitives --------------------------------------------------------


def test_tokenize_is_lowercase_alnum() -> None:
    assert tokenize("Hello-World_42") == ["hello", "world_42"]
    assert tokenize("POLICY#S8.p2") == ["policy", "s8", "p2"]


def test_bm25_search_is_deterministic(tiny_corpus: list[FactChunk]) -> None:
    index = BM25Index(tiny_corpus)
    first = index.search("zulassungskriterium", top_k=3)
    second = index.search("zulassungskriterium", top_k=3)
    assert first == second
    assert first  # non-empty
    assert first[0][0] == 1  # POLICY#S8.p2


def test_bm25_tiebreak_by_fact_id() -> None:
    chunks = [
        FactChunk(
            fact_id=f"FAKE#{label}",
            kind="policy",
            source_path="fake.md",
            line_start=1,
            line_end=1,
            text="shared token shared token",
            sha256="0" * 64,
            tags=(),
        )
        for label in ("zzz", "aaa", "mmm")
    ]
    index = BM25Index(chunks)
    hits = index.search("shared", top_k=3)
    assert [index.chunk_at(i).fact_id for i, _ in hits] == [
        "FAKE#aaa",
        "FAKE#mmm",
        "FAKE#zzz",
    ]


def test_empty_query_returns_no_hits(tiny_corpus: list[FactChunk]) -> None:
    index = BM25Index(tiny_corpus)
    assert index.search("", top_k=3) == []
    assert index.search("   ", top_k=3) == []


# --- Engine integration -----------------------------------------------------


def test_engine_retrieve_and_cite_roundtrip(repo_root: Path) -> None:
    clear_engine_cache()
    clear_memory_cache()
    engine = RetrievalEngine.for_repo(repo_root)
    hits = engine.retrieve("POLICY Zulassungskriterien", top_k=3)
    assert hits, "expected at least one hit for the acceptance-criteria query"
    top = hits[0]
    assert top.fact_id.startswith("POLICY#S8."), (
        f"expected POLICY#S8.* as top hit, got {top.fact_id}"
    )
    chunk = engine.cite(top.fact_id)
    assert chunk is not None
    assert chunk.sha256 == top.sha256


def test_engine_filter_by_kind(repo_root: Path) -> None:
    clear_engine_cache()
    engine = RetrievalEngine.for_repo(repo_root)
    hits = engine.retrieve("rationale", top_k=10, kind="signal")
    assert hits
    assert all(h.kind == "signal" for h in hits)


def test_engine_unknown_fact_id_returns_none(repo_root: Path) -> None:
    clear_engine_cache()
    engine = RetrievalEngine.for_repo(repo_root)
    assert engine.cite("NOT_A_REAL_ID#missing") is None


# --- Gold-set precision -----------------------------------------------------

# Hand-curated query -> expected fact_id prefix pairs. Each entry asserts
# that the expected prefix appears somewhere in the top 5 hits. Curated
# against the MVP corpus (ADR-091 acceptance criterion 4, >= 80%).
GOLD_SET: list[tuple[str, str]] = [
    ("POLICY Zulassungskriterien", "POLICY#S8."),
    ("Audit Pflicht Risiko", "POLICY#S18."),
    ("Telemetrie Datenschutz", "POLICY#S19."),
    ("Produktziel drift", "POLICY#S4."),
    ("Grundsatz Qualitaet Glaubwuerdigkeit", "POLICY#S3."),
    ("kNN Semantic Search verworfen", "ADR-031#"),
    ("Retrieval RAG grounding", "ADR-091#"),
    ("agent telemetry schema", "ADR-090#"),
    ("autonomer agent regelkreis severity gate", "ADR-089#"),
    ("blast radius engine", "ADR-087#"),
    ("trend gate enforcement", "ADR-086#"),
    ("drift nudge cold start", "ADR-085#"),
    ("vibe coding tool positionierung", "ADR-084#"),
    ("outcome feedback ledger", "ADR-088#"),
    ("agent pre-edit pattern scan", "ADR-083#"),
]


def test_gold_set_precision_at_5(repo_root: Path) -> None:
    clear_engine_cache()
    engine = RetrievalEngine.for_repo(repo_root)
    hits_per_query: list[tuple[str, str, bool]] = []
    for query, expected_prefix in GOLD_SET:
        results = engine.retrieve(query, top_k=5)
        matched = any(r.fact_id.startswith(expected_prefix) for r in results)
        hits_per_query.append((query, expected_prefix, matched))

    total = len(GOLD_SET)
    matched_count = sum(1 for _, _, m in hits_per_query if m)
    precision = matched_count / total
    misses = [
        (q, p) for q, p, m in hits_per_query if not m
    ]
    assert precision >= 0.80, (
        f"gold-set precision@5 below 80%: {precision:.2%} "
        f"({matched_count}/{total}); misses={misses}"
    )
