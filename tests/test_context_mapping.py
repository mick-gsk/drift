"""Tests for scripts/_context_mapping.py — contract and file existence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _context_mapping as ctx  # noqa: E402
from get_context_hints import get_context_hints  # noqa: E402

# ---------------------------------------------------------------------------
# Task-type mapping tests
# ---------------------------------------------------------------------------

def test_every_valid_task_type_has_entry() -> None:
    for task_type in ctx.VALID_TASK_TYPES:
        assert task_type in ctx.CONTEXT_PATHS
        assert ctx.CONTEXT_PATHS[task_type], f"empty context for {task_type}"


def test_no_entry_exceeds_budget() -> None:
    for task_type, paths in ctx.CONTEXT_PATHS.items():
        assert len(paths) <= ctx.MAX_PATHS_PER_TYPE, f"{task_type} exceeds budget"


@pytest.mark.parametrize("task_type", ctx.VALID_TASK_TYPES)
def test_all_referenced_paths_exist(task_type: str) -> None:
    """Every referenced path must resolve to an existing file — catches renames."""
    for rel_path in ctx.CONTEXT_PATHS[task_type]:
        full = REPO_ROOT / rel_path
        assert full.is_file(), f"missing file referenced by {task_type!r}: {rel_path}"


def test_context_for_rejects_unknown_type() -> None:
    with pytest.raises(KeyError):
        ctx.context_for("nonsense")


def test_no_policy_text_leaks_into_mapping() -> None:
    """Regression guard: mapping values must be paths only, not prose."""
    for paths in ctx.CONTEXT_PATHS.values():
        for path in paths:
            assert path.endswith(".md"), f"non-md path leaks policy ambiguity: {path}"
            assert " " not in path, f"path contains space (likely prose): {path!r}"
            assert len(path) < 200, f"path suspiciously long: {path!r}"


# ---------------------------------------------------------------------------
# Signal-level context manifest tests (just-in-time injection)
# ---------------------------------------------------------------------------

_MIN_MAPPED_SIGNALS = 3


def test_signal_manifest_covers_minimum_signals() -> None:
    """At least MIN_MAPPED_SIGNALS signal IDs must have a dedicated entry."""
    assert len(ctx.SIGNAL_CONTEXT_PATHS) >= _MIN_MAPPED_SIGNALS, (
        f"SIGNAL_CONTEXT_PATHS covers only {len(ctx.SIGNAL_CONTEXT_PATHS)} signals; "
        f"minimum required is {_MIN_MAPPED_SIGNALS}"
    )


def test_no_signal_entry_is_empty() -> None:
    for signal_id, paths in ctx.SIGNAL_CONTEXT_PATHS.items():
        assert paths, f"empty context tuple for signal {signal_id!r}"


def test_no_signal_entry_exceeds_budget() -> None:
    for signal_id, paths in ctx.SIGNAL_CONTEXT_PATHS.items():
        assert len(paths) <= ctx.MAX_PATHS_PER_SIGNAL, (
            f"signal {signal_id!r} has {len(paths)} paths, "
            f"exceeds MAX_PATHS_PER_SIGNAL={ctx.MAX_PATHS_PER_SIGNAL}"
        )


@pytest.mark.parametrize("signal_id", sorted(ctx.SIGNAL_CONTEXT_PATHS))
def test_signal_context_paths_exist(signal_id: str) -> None:
    """Every path referenced by a signal must resolve to an existing file."""
    for rel_path in ctx.SIGNAL_CONTEXT_PATHS[signal_id]:
        full = REPO_ROOT / rel_path
        assert full.is_file(), (
            f"signal {signal_id!r}: missing file {rel_path}"
        )


def test_signal_context_paths_are_md_files() -> None:
    """Regression guard: signal context paths must be .md files, not prose."""
    for signal_id, paths in ctx.SIGNAL_CONTEXT_PATHS.items():
        for path in paths:
            assert path.endswith(".md"), (
                f"signal {signal_id!r}: non-.md path: {path!r}"
            )
            assert " " not in path, (
                f"signal {signal_id!r}: path contains space: {path!r}"
            )
            assert len(path) < 200, (
                f"signal {signal_id!r}: path suspiciously long: {path!r}"
            )


def test_signal_context_for_known_signal() -> None:
    """signal_context_for returns the expected paths for a known signal."""
    paths = ctx.signal_context_for("architecture_violation")
    assert paths, "architecture_violation must have at least one context path"
    assert any("avs.md" in p for p in paths), (
        "architecture_violation context must include the signal reference doc (avs.md)"
    )


def test_signal_context_for_unknown_signal_returns_empty() -> None:
    """signal_context_for returns an empty tuple for unmapped signals."""
    result = ctx.signal_context_for("not_a_real_signal")
    assert result == (), f"expected empty tuple, got {result!r}"


def test_architecture_violation_has_adr_context() -> None:
    """architecture_violation must include at least one ADR path for design context."""
    paths = ctx.signal_context_for("architecture_violation")
    assert any("ADR-" in p for p in paths), (
        "architecture_violation should include at least one ADR for design context"
    )


def test_security_signals_have_dedicated_entries() -> None:
    """Security signals (MAZ, ISD, HSC) must each have a dedicated context entry."""
    for signal_id in ("missing_authorization", "insecure_default", "hardcoded_secret"):
        paths = ctx.signal_context_for(signal_id)
        assert paths, f"security signal {signal_id!r} must have context paths"


# ---------------------------------------------------------------------------
# get_context_hints.py tests (JIT injection helper)
# ---------------------------------------------------------------------------


def test_get_context_hints_known_signals(tmp_path: Path) -> None:
    """get_context_hints returns paths for signals present in a report."""
    report = tmp_path / "drift.json"
    report.write_text(
        json.dumps({"findings": [
            {"signal": "architecture_violation"}, {"signal": "pattern_fragmentation"},
        ]}),
        encoding="utf-8",
    )
    hints = get_context_hints(report)
    assert hints, "expected non-empty hints for known signals"
    assert "docs-site/reference/signals/avs.md" in hints, "expected avs.md in hints"
    assert "docs-site/reference/signals/pfs.md" in hints, "expected pfs.md in hints"


def test_get_context_hints_unknown_signals(tmp_path: Path) -> None:
    """get_context_hints returns empty list when no signals are mapped."""
    report = tmp_path / "drift.json"
    report.write_text(
        json.dumps({"findings": [{"signal": "not_a_real_signal"}]}),
        encoding="utf-8",
    )
    assert get_context_hints(report) == []


def test_get_context_hints_missing_file(tmp_path: Path) -> None:
    """get_context_hints returns empty list when the report file does not exist."""
    assert get_context_hints(tmp_path / "no_such_file.json") == []


def test_get_context_hints_no_findings(tmp_path: Path) -> None:
    """get_context_hints returns empty list when the report has no findings."""
    report = tmp_path / "drift.json"
    report.write_text(json.dumps({"findings": []}), encoding="utf-8")
    assert get_context_hints(report) == []


def test_get_context_hints_respects_max_hints(tmp_path: Path) -> None:
    """get_context_hints never returns more paths than the max_hints cap."""
    # Use all known signals to generate a large candidate list.
    signals = list(ctx.SIGNAL_CONTEXT_PATHS.keys())
    report = tmp_path / "drift.json"
    report.write_text(
        json.dumps({"findings": [{"signal": s} for s in signals]}),
        encoding="utf-8",
    )
    hints = get_context_hints(report, max_hints=3)
    assert len(hints) <= 3, f"expected at most 3 hints, got {len(hints)}"


def test_get_context_hints_deduplicates(tmp_path: Path) -> None:
    """get_context_hints returns no duplicate paths even with repeated signals."""
    report = tmp_path / "drift.json"
    report.write_text(
        json.dumps({"findings": [
            {"signal": "architecture_violation"}, {"signal": "architecture_violation"},
        ]}),
        encoding="utf-8",
    )
    hints = get_context_hints(report)
    assert len(hints) == len(set(hints)), "duplicate paths found in context hints"

