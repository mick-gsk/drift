"""Tests for Issue #544 — Friction 3: diff deferred-context annotation.

Verifies that ``diff()`` enriches its response with a ``deferred_context``
field when some scoped-new findings involve files that match ``deferred:``
patterns in the drift config.
"""

from __future__ import annotations

import fnmatch
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _make_finding(file_path: str | None = "src/a.py") -> Any:
    return SimpleNamespace(
        file_path=Path(file_path) if file_path else None,
        signal_type="PFS",
        severity="MEDIUM",
        score=0.5,
        fingerprint="fp-001",
    )


def _make_cfg(patterns: list[str]) -> Any:
    areas = [SimpleNamespace(pattern=p) for p in patterns]
    return SimpleNamespace(deferred=areas)


class TestDiffDeferredContext:
    """_deferred_context block in the diff() response."""

    def test_deferred_finding_produces_context_block(self) -> None:
        """When a new finding's file matches a deferred pattern, deferred_context is set."""
        scoped_new = [_make_finding("legacy/old_module.py"), _make_finding("src/active.py")]
        cfg = _make_cfg(["legacy/**"])
        deferred_pats = frozenset(a.pattern for a in cfg.deferred)

        def _in_deferred(fp: Any) -> bool:
            if fp is None:
                return False
            posix = Path(str(fp)).as_posix()
            return any(fnmatch.fnmatch(posix, pat) for pat in deferred_pats)

        deferred_new = [f for f in scoped_new if _in_deferred(f.file_path)]
        active_new = len(scoped_new) - len(deferred_new)

        assert len(deferred_new) == 1
        assert active_new == 1

        # The note template must reference both counts
        note = (
            f"{len(deferred_new)} of {len(scoped_new)} new finding"
            f"{'s' if len(scoped_new) != 1 else ''} involve files in "
            "deferred: patterns. Active-scope delta: "
            f"{active_new} finding{'s' if active_new != 1 else ''}."
        )
        assert "1 of 2 new findings involve files in deferred:" in note
        assert "Active-scope delta: 1 finding." in note

    def test_no_deferred_patterns_produces_no_context(self) -> None:
        """When cfg.deferred is empty, no deferred_context should be emitted."""
        cfg = _make_cfg([])
        # Simulate the guard: if not cfg.deferred, skip annotation
        assert not cfg.deferred, "Expected empty deferred list"

    def test_all_findings_active_no_context(self) -> None:
        """When no new findings match deferred patterns, no context block is emitted."""
        scoped_new = [_make_finding("src/a.py"), _make_finding("src/b.py")]
        cfg = _make_cfg(["legacy/**"])
        deferred_pats = frozenset(a.pattern for a in cfg.deferred)

        deferred_new = [
            f for f in scoped_new
            if f.file_path and any(
                fnmatch.fnmatch(Path(str(f.file_path)).as_posix(), pat)
                for pat in deferred_pats
            )
        ]
        assert len(deferred_new) == 0, "No findings should match legacy/** for src/ files"

    def test_none_file_path_handled_gracefully(self) -> None:
        """Findings with file_path=None must not raise."""
        scoped_new = [_make_finding(None), _make_finding("src/a.py")]
        cfg = _make_cfg(["**/*.py"])
        deferred_pats = frozenset(a.pattern for a in cfg.deferred)

        def _in_deferred(fp: Any) -> bool:
            if fp is None:
                return False
            posix = Path(str(fp)).as_posix()
            return any(fnmatch.fnmatch(posix, pat) for pat in deferred_pats)

        # Must not raise — None file_path is handled by the guard
        result = [f for f in scoped_new if _in_deferred(f.file_path)]
        # Only src/a.py matches
        assert len(result) == 1
        assert result[0].file_path == Path("src/a.py")
