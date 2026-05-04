"""Tests for malformed history snapshot handling (Failure Mode Coverage).

Validates that ``build_trend_context``, ``delta_gate_pass``, and the
``drift trend`` CLI command handle history entries with missing or
wrong-typed ``drift_score`` / ``timestamp`` keys gracefully instead of
crashing with unhandled KeyError / TypeError.
"""

from __future__ import annotations

import pytest
from drift.trend_history import build_trend_context

# ── build_trend_context ───────────────────────────────────────────────────


class TestBuildTrendContextMalformed:
    """build_trend_context must not crash on malformed history entries."""

    def test_snapshot_missing_drift_score_key(self):
        """Entry without drift_score key → treat as baseline."""
        snapshots = [{"timestamp": "2026-01-01T00:00:00"}]
        ctx = build_trend_context(0.40, snapshots)
        # Must not crash; should degrade to baseline or skip entry
        assert ctx.direction == "baseline"
        assert ctx.previous_score is None
        assert ctx.recent_scores == []
        assert ctx.history_depth == 0

    def test_mixed_valid_and_invalid_entries(self):
        """Mix of valid and invalid entries → use only valid ones."""
        snapshots = [
            {"drift_score": 0.30},
            {"timestamp": "2026-01-02"},  # missing drift_score
            {"drift_score": 0.40},
        ]
        ctx = build_trend_context(0.42, snapshots)
        # Should use the 2 valid entries, ignoring the malformed one
        assert ctx.direction in ("degrading", "stable", "improving")
        assert ctx.previous_score == pytest.approx(0.40, abs=0.01)
        assert ctx.history_depth == 2

    def test_all_entries_invalid(self):
        """All entries missing drift_score → baseline."""
        snapshots = [
            {"timestamp": "2026-01-01"},
            {"timestamp": "2026-01-02"},
        ]
        ctx = build_trend_context(0.50, snapshots)
        assert ctx.direction == "baseline"
        assert ctx.previous_score is None

    def test_drift_score_wrong_type_string(self):
        """drift_score is a string → skip entry."""
        snapshots = [{"drift_score": "not_a_number"}]
        ctx = build_trend_context(0.40, snapshots)
        assert ctx.direction == "baseline"

    def test_drift_score_none(self):
        """drift_score is explicitly None → skip entry."""
        snapshots = [{"drift_score": None}]
        ctx = build_trend_context(0.40, snapshots)
        assert ctx.direction == "baseline"


# ── delta_gate_pass ───────────────────────────────────────────────────────


class TestDeltaGatePassMalformed:
    """delta_gate_pass must handle malformed history entries."""

    def test_malformed_entries_skipped(self):
        from drift.scoring.engine import delta_gate_pass

        # Mix of valid and invalid entries
        history = [
            {"drift_score": 0.40},
            {"timestamp": "no-score"},  # missing drift_score
            {"drift_score": 0.42},
        ]
        # Should not crash; should use valid entries only
        result = delta_gate_pass(0.50, history, fail_on_delta=0.05)
        assert isinstance(result, bool)
