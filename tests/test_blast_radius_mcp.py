"""MCP-A2A-Integrationstests für blast_radius (ADR-087)."""

from __future__ import annotations

from pathlib import Path

import pytest

from drift.serve.a2a_router import _ensure_dispatch_table


@pytest.fixture
def repo_root() -> Path:
    path = Path(__file__).resolve().parents[1]
    # After ADR-100 monorepo migration, the canonical drift source lives under
    # packages/drift/src/drift (compat stub) instead of src/drift.
    assert (path / "packages" / "drift" / "src" / "drift").is_dir()
    return path


def test_blast_radius_registered_in_dispatch() -> None:
    table = _ensure_dispatch_table()
    assert "blast_radius" in table


def test_blast_radius_handler_returns_summary(repo_root: Path) -> None:
    table = _ensure_dispatch_table()
    handler = table["blast_radius"]
    result = handler(
        {
            "path": str(repo_root),
            "changed_files": ["POLICY.md"],
        }
    )
    assert "summary" in result
    summary = result["summary"]
    assert summary["impact_count"] >= 1
    assert summary["requires_maintainer_ack"] is True
    assert "top_impacts" in summary


def test_blast_radius_handler_rejects_non_list_changed_files(
    repo_root: Path,
) -> None:
    table = _ensure_dispatch_table()
    handler = table["blast_radius"]
    with pytest.raises(ValueError, match="changed_files"):
        handler({"path": str(repo_root), "changed_files": "POLICY.md"})


def test_blast_radius_handler_persist_false_by_default(
    repo_root: Path,
) -> None:
    table = _ensure_dispatch_table()
    handler = table["blast_radius"]
    result = handler(
        {"path": str(repo_root), "changed_files": ["README.md"]}
    )
    assert "persisted_to" not in result
