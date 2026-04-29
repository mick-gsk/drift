"""Tests for drift_retrieve / drift_cite MCP tool routers (ADR-091)."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Coroutine, cast

import pytest

from drift.mcp_router_retrieval import run_cite, run_retrieve
from drift.retrieval.search import clear_engine_cache


@pytest.fixture(scope="module")
def repo_root() -> Path:
    # ADR-099: tests live in src/drift/retrieval/tests/, repo root is 4 levels up.
    return Path(__file__).resolve().parents[4]


@pytest.fixture(autouse=True)
def _isolate_engine_cache() -> None:
    clear_engine_cache()


def _call(coro: Coroutine[Any, Any, str]) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(asyncio.run(coro)))


def test_retrieve_happy_path(repo_root: Path) -> None:
    payload = _call(
        run_retrieve(
            path=str(repo_root),
            query="POLICY Zulassungskriterien",
            top_k=3,
            kind=None,
            signal_id=None,
        )
    )
    assert "error" not in payload
    assert payload["chunk_count"] > 0
    assert payload["results"]
    top = payload["results"][0]
    assert top["fact_id"].startswith("POLICY#S8.")
    assert top["sha256"]
    assert payload["agent_instruction"].startswith("Cite")
    # corpus_sha256 is exposed for reproducibility anchors.
    assert len(payload["corpus_sha256"]) == 64


def test_retrieve_empty_query_rejected(repo_root: Path) -> None:
    payload = _call(
        run_retrieve(
            path=str(repo_root),
            query="   ",
            top_k=5,
            kind=None,
            signal_id=None,
        )
    )
    assert payload["error_code"] == "DRIFT-RAG-001"


def test_retrieve_invalid_kind_rejected(repo_root: Path) -> None:
    payload = _call(
        run_retrieve(
            path=str(repo_root),
            query="anything",
            top_k=5,
            kind="bogus",
            signal_id=None,
        )
    )
    assert payload["error_code"] == "DRIFT-RAG-003"


def test_retrieve_filters_by_kind(repo_root: Path) -> None:
    payload = _call(
        run_retrieve(
            path=str(repo_root),
            query="rationale",
            top_k=5,
            kind="signal",
            signal_id=None,
        )
    )
    assert "error" not in payload
    assert payload["results"]
    assert all(r["kind"] == "signal" for r in payload["results"])


def test_cite_roundtrip(repo_root: Path) -> None:
    retrieved = _call(
        run_retrieve(
            path=str(repo_root),
            query="POLICY Zulassungskriterien",
            top_k=1,
            kind=None,
            signal_id=None,
        )
    )
    fact_id = retrieved["results"][0]["fact_id"]
    original_sha = retrieved["results"][0]["sha256"]
    cited = _call(run_cite(path=str(repo_root), fact_id=fact_id))
    assert cited["fact_id"] == fact_id
    assert cited["sha256"] == original_sha
    assert cited["migrated"] is False
    assert cited["text"]


def test_cite_unknown_fact_id(repo_root: Path) -> None:
    payload = _call(run_cite(path=str(repo_root), fact_id="NOT#real"))
    assert payload["error_code"] == "DRIFT-RAG-006"


def test_cite_empty_fact_id(repo_root: Path) -> None:
    payload = _call(run_cite(path=str(repo_root), fact_id=""))
    assert payload["error_code"] == "DRIFT-RAG-005"


def test_tools_registered_in_mcp_server() -> None:
    """Ensure FastMCP registers both new tools."""
    pytest.importorskip("mcp")
    import drift.mcp_server as server

    tool_names = {f.__name__ for f in server._EXPORTED_MCP_TOOLS}
    assert "drift_retrieve" in tool_names
    assert "drift_cite" in tool_names
