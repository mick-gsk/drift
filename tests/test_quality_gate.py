"""Tests for drift.quality_gate — quality-drift detection between runs.

Decision: ADR-029
"""

from __future__ import annotations

from drift.quality_gate import (
    RunSnapshot,
    compare_runs,
    quality_drift_from_history,
)


class TestCompareRuns:
    def test_improving(self):
        before = RunSnapshot(score=50.0, finding_count=20)
        after = RunSnapshot(score=45.0, finding_count=15)
        qd = compare_runs(before, after)
        assert qd.direction == "improving"
        assert qd.score_delta == -5.0
        assert qd.finding_delta == -5
        assert "improved" in qd.advisory

    def test_degrading(self):
        before = RunSnapshot(score=30.0, finding_count=10)
        after = RunSnapshot(score=35.0, finding_count=15)
        qd = compare_runs(before, after)
        assert qd.direction == "degrading"
        assert qd.score_delta == 5.0
        assert qd.finding_delta == 5
        assert "worsened" in qd.advisory

    def test_stable(self):
        before = RunSnapshot(score=40.0, finding_count=12)
        after = RunSnapshot(score=40.3, finding_count=12)
        qd = compare_runs(before, after)
        assert qd.direction == "stable"
        assert "stable" in qd.advisory.lower()

    def test_score_improving_findings_stable(self):
        before = RunSnapshot(score=50.0, finding_count=10)
        after = RunSnapshot(score=44.0, finding_count=10)
        qd = compare_runs(before, after)
        assert qd.direction == "improving"

    def test_findings_degrading_score_stable(self):
        before = RunSnapshot(score=40.0, finding_count=10)
        after = RunSnapshot(score=40.2, finding_count=12)
        qd = compare_runs(before, after)
        assert qd.direction == "degrading"

    def test_custom_tolerances_can_mark_small_regression_as_stable(self):
        before = RunSnapshot(score=40.0, finding_count=10)
        after = RunSnapshot(score=40.8, finding_count=11)

        qd = compare_runs(
            before,
            after,
            score_tolerance=1.0,
            finding_tolerance=1,
        )

        assert qd.direction == "stable"


class TestQualityDriftFromHistory:
    def test_empty_history(self):
        result = quality_drift_from_history([])
        assert result is None

    def test_single_entry(self):
        result = quality_drift_from_history([{"score": 50.0, "finding_count": 20}])
        assert result is None

    def test_two_entries(self):
        history = [
            {"score": 50.0, "finding_count": 20, "tool_calls_at": 5},
            {"score": 45.0, "finding_count": 18, "tool_calls_at": 10},
        ]
        qd = quality_drift_from_history(history)
        assert qd is not None
        assert qd.direction == "improving"

    def test_uses_last_two(self):
        history = [
            {"score": 50.0, "finding_count": 20},
            {"score": 45.0, "finding_count": 18},
            {"score": 48.0, "finding_count": 22},
        ]
        qd = quality_drift_from_history(history)
        assert qd is not None
        # Compares last two: 45→48, degrading
        assert qd.direction == "degrading"

    def test_missing_score_in_prev_raises_valueerror(self):
        import pytest

        with pytest.raises(ValueError, match="run_history\\[0\\].*score"):
            quality_drift_from_history([
                {"finding_count": 5},
                {"score": 38.0, "finding_count": 5},
            ])

    def test_missing_finding_count_in_prev_raises_valueerror(self):
        import pytest

        with pytest.raises(ValueError, match="run_history\\[0\\].*finding_count"):
            quality_drift_from_history([
                {"score": 42.0},
                {"score": 38.0, "finding_count": 5},
            ])

    def test_missing_score_in_curr_raises_valueerror(self):
        import pytest

        with pytest.raises(ValueError, match="run_history\\[1\\].*score"):
            quality_drift_from_history([
                {"score": 42.0, "finding_count": 3},
                {"finding_count": 5},
            ])

    def test_error_message_names_missing_keys(self):
        import pytest

        with pytest.raises(ValueError, match="finding_count") as exc_info:
            quality_drift_from_history([
                {"score": 42.0},
                {"score": 38.0, "finding_count": 5},
            ])
        assert "run_history[0]" in str(exc_info.value)

    def test_custom_tolerances_are_forwarded_to_compare(self):
        history = [
            {"score": 40.0, "finding_count": 10, "tool_calls_at": 1},
            {"score": 40.8, "finding_count": 11, "tool_calls_at": 2},
        ]

        qd = quality_drift_from_history(
            history,
            score_tolerance=1.0,
            finding_tolerance=1,
        )

        assert qd is not None
        assert qd.direction == "stable"
