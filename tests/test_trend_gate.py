"""Tests for trend-gate enforcement: evaluate_trend_gate, remediation helpers, and CLI."""

from __future__ import annotations

import pytest
from drift.quality_gate import TrendGateDecision, evaluate_trend_gate
from drift.remediation_activity import (
    finding_fingerprints,
    has_remediation_activity,
    resolved_fingerprints,
)

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

def _snap(score: float, commit: str | None = None, fps: list[str] | None = None) -> dict:
    s: dict = {"drift_score": score}
    if commit is not None:
        s["commit_hash"] = commit
    if fps is not None:
        s["finding_fingerprints"] = fps
    return s


# ---------------------------------------------------------------------------
# evaluate_trend_gate
# ---------------------------------------------------------------------------

class TestEvaluateTrendGate:
    def test_raises_on_window_less_than_two(self):
        with pytest.raises(ValueError, match="window_commits must be >= 2"):
            evaluate_trend_gate(
                snapshots=[],
                window_commits=1,
                delta_threshold=0.05,
                require_remediation_activity=True,
            )

    def test_insufficient_history_returns_not_blocked(self):
        result = evaluate_trend_gate(
            snapshots=[_snap(10.0, "aaa")],
            window_commits=3,
            delta_threshold=0.05,
            require_remediation_activity=True,
        )
        assert result.blocked is False
        assert result.reason == "insufficient_history"

    def test_empty_history_returns_not_blocked(self):
        result = evaluate_trend_gate(
            snapshots=[],
            window_commits=2,
            delta_threshold=0.05,
            require_remediation_activity=True,
        )
        assert result.blocked is False

    def test_below_delta_threshold_returns_not_blocked(self):
        snapshots = [_snap(10.0, "aaa"), _snap(10.02, "bbb")]
        result = evaluate_trend_gate(
            snapshots=snapshots,
            window_commits=2,
            delta_threshold=0.05,
            require_remediation_activity=True,
        )
        assert result.blocked is False
        assert result.reason == "below_delta_threshold"
        assert result.score_delta == pytest.approx(0.02, abs=1e-4)

    def test_above_threshold_no_remediation_blocks(self):
        snapshots = [_snap(10.0, "aaa"), _snap(10.1, "bbb")]
        result = evaluate_trend_gate(
            snapshots=snapshots,
            window_commits=2,
            delta_threshold=0.05,
            require_remediation_activity=True,
        )
        assert result.blocked is True
        assert result.reason == "degradation_without_remediation"

    def test_above_threshold_with_remediation_not_blocked(self):
        fps_before = ["fp1", "fp2"]
        fps_after = ["fp2"]  # fp1 resolved
        snapshots = [
            _snap(10.0, "aaa", fps_before),
            _snap(10.1, "bbb", fps_after),
        ]
        result = evaluate_trend_gate(
            snapshots=snapshots,
            window_commits=2,
            delta_threshold=0.05,
            require_remediation_activity=True,
        )
        assert result.blocked is False
        assert result.reason == "remediation_detected"
        assert result.remediation_activity_detected is True

    def test_above_threshold_require_false_blocks_regardless(self):
        fps_before = ["fp1", "fp2"]
        fps_after = ["fp2"]
        snapshots = [
            _snap(10.0, "aaa", fps_before),
            _snap(10.1, "bbb", fps_after),
        ]
        result = evaluate_trend_gate(
            snapshots=snapshots,
            window_commits=2,
            delta_threshold=0.05,
            require_remediation_activity=False,
        )
        assert result.blocked is True
        assert result.reason == "degradation_threshold_exceeded"

    def test_window_deduplication_by_commit_hash(self):
        # Same commit hash appears twice — should count once
        snapshots = [
            _snap(10.0, "aaa"),
            _snap(10.0, "aaa"),  # duplicate
            _snap(10.1, "bbb"),
        ]
        result = evaluate_trend_gate(
            snapshots=snapshots,
            window_commits=2,
            delta_threshold=0.05,
            require_remediation_activity=False,
        )
        # Only 2 unique commits in window → sufficient
        assert result.history_points == 2

    def test_history_points_reflects_window_size(self):
        snapshots = [_snap(10.0, "aaa"), _snap(10.05, "bbb"), _snap(10.1, "ccc")]
        result = evaluate_trend_gate(
            snapshots=snapshots,
            window_commits=3,
            delta_threshold=0.05,
            require_remediation_activity=True,
        )
        assert result.history_points == 3

    def test_return_type(self):
        snapshots = [_snap(10.0, "aaa"), _snap(10.1, "bbb")]
        result = evaluate_trend_gate(
            snapshots=snapshots,
            window_commits=2,
            delta_threshold=0.05,
            require_remediation_activity=True,
        )
        assert isinstance(result, TrendGateDecision)


# ---------------------------------------------------------------------------
# finding_fingerprints
# ---------------------------------------------------------------------------

class TestFindingFingerprints:
    def test_returns_set_from_list(self):
        snap = {"finding_fingerprints": ["fp1", "fp2", "fp3"]}
        assert finding_fingerprints(snap) == {"fp1", "fp2", "fp3"}

    def test_missing_key_returns_empty(self):
        assert finding_fingerprints({}) == set()

    def test_non_list_value_returns_empty(self):
        assert finding_fingerprints({"finding_fingerprints": "fp1"}) == set()

    def test_filters_non_strings(self):
        snap = {"finding_fingerprints": ["fp1", None, 42, "fp2"]}
        assert finding_fingerprints(snap) == {"fp1", "fp2"}

    def test_filters_empty_strings(self):
        snap = {"finding_fingerprints": ["fp1", "", "fp2"]}
        assert finding_fingerprints(snap) == {"fp1", "fp2"}


# ---------------------------------------------------------------------------
# resolved_fingerprints
# ---------------------------------------------------------------------------

class TestResolvedFingerprints:
    def test_returns_fps_present_before_absent_after(self):
        before = {"finding_fingerprints": ["fp1", "fp2", "fp3"]}
        after = {"finding_fingerprints": ["fp2"]}
        assert resolved_fingerprints(before, after) == {"fp1", "fp3"}

    def test_no_resolved_if_identical(self):
        snap = {"finding_fingerprints": ["fp1"]}
        assert resolved_fingerprints(snap, snap) == set()

    def test_empty_before_returns_empty(self):
        after = {"finding_fingerprints": ["fp1"]}
        assert resolved_fingerprints({}, after) == set()


# ---------------------------------------------------------------------------
# has_remediation_activity
# ---------------------------------------------------------------------------

class TestHasRemediationActivity:
    def test_returns_false_if_fewer_than_two_snapshots(self):
        assert has_remediation_activity([_snap(10.0, "aaa", ["fp1"])], window_commits=2) is False

    def test_returns_false_if_window_commits_less_than_two(self):
        snaps = [_snap(10.0, "aaa", ["fp1"]), _snap(10.0, "bbb", [])]
        assert has_remediation_activity(snaps, window_commits=1) is False

    def test_detects_resolved_fingerprint(self):
        snaps = [
            _snap(10.0, "aaa", ["fp1", "fp2"]),
            _snap(10.0, "bbb", ["fp2"]),
        ]
        assert has_remediation_activity(snaps, window_commits=2) is True

    def test_returns_false_when_no_resolution(self):
        snaps = [
            _snap(10.0, "aaa", ["fp1", "fp2"]),
            _snap(10.0, "bbb", ["fp1", "fp2"]),
        ]
        assert has_remediation_activity(snaps, window_commits=2) is False

    def test_skips_same_commit_pairs(self):
        # Two snaps with same commit_hash: treat as single run, no resolution counted
        snaps = [
            _snap(10.0, "aaa", ["fp1", "fp2"]),
            _snap(10.0, "aaa", ["fp2"]),  # same commit
        ]
        assert has_remediation_activity(snaps, window_commits=2) is False

    def test_true_if_any_commit_resolves(self):
        snaps = [
            _snap(10.0, "aaa", ["fp1", "fp2"]),
            _snap(10.0, "bbb", ["fp1", "fp2"]),  # no resolution here
            _snap(10.0, "ccc", ["fp2"]),  # fp1 resolved here
        ]
        assert has_remediation_activity(snaps, window_commits=3) is True
