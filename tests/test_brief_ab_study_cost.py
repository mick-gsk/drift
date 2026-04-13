"""Tests for the cost model and aggregation helpers in scripts/brief_ab_study.py."""

from __future__ import annotations

import importlib
import math
import sys
from pathlib import Path
from typing import Any

import pytest

# Import the study script as a module
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
brief_ab_study = importlib.import_module("brief_ab_study")

_error_cost_default = brief_ab_study._error_cost_default
_error_cost_robust = brief_ab_study._error_cost_robust
_patch_line_count = brief_ab_study._patch_line_count
_aggregate_by_task = brief_ab_study._aggregate_by_task
_SEVERITY_WEIGHTS = brief_ab_study._SEVERITY_WEIGHTS


# ---------------------------------------------------------------------------
# _error_cost_default
# ---------------------------------------------------------------------------


class TestErrorCostDefault:
    def test_empty_findings(self) -> None:
        assert _error_cost_default([]) == 0.0

    def test_single_critical(self) -> None:
        findings = [{"severity": "critical"}]
        assert _error_cost_default(findings) == 8.0

    def test_mixed_severities(self) -> None:
        findings = [
            {"severity": "critical"},
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
            {"severity": "info"},
        ]
        # 8 + 4 + 2 + 1 + 0 = 15
        assert _error_cost_default(findings) == 15.0

    def test_info_contributes_zero(self) -> None:
        assert _error_cost_default([{"severity": "info"}]) == 0.0

    def test_unknown_severity_contributes_zero(self) -> None:
        assert _error_cost_default([{"severity": "unknown"}]) == 0.0

    def test_missing_severity_key(self) -> None:
        assert _error_cost_default([{"signal": "pfs"}]) == 0.0

    def test_case_insensitive(self) -> None:
        assert _error_cost_default([{"severity": "HIGH"}]) == 4.0
        assert _error_cost_default([{"severity": "Critical"}]) == 8.0

    def test_multiple_same_severity(self) -> None:
        findings = [{"severity": "medium"}] * 5
        assert _error_cost_default(findings) == 10.0


# ---------------------------------------------------------------------------
# _error_cost_robust
# ---------------------------------------------------------------------------


class TestErrorCostRobust:
    def test_empty_findings(self) -> None:
        assert _error_cost_robust([]) == 0.0

    def test_info_contributes_zero(self) -> None:
        assert _error_cost_robust([{"severity": "info", "signal": "pfs"}]) == 0.0

    def test_single_finding_no_related_files(self) -> None:
        findings = [{"severity": "high", "signal": "pattern_fragmentation"}]
        # h=2.0, w_sev=4, breadth=min(4.0, 1+ln(1+0))=1.0
        expected = 2.0 * 4 * 1.0
        assert _error_cost_robust(findings) == expected

    def test_breadth_with_related_files(self) -> None:
        findings = [{
            "severity": "high",
            "signal": "pattern_fragmentation",
            "related_files": ["a.py", "b.py", "c.py"],
        }]
        # h=2.0, w_sev=4, breadth=min(4.0, 1+ln(4))≈2.386
        breadth = min(4.0, 1 + math.log(1 + 3))
        expected = round(2.0 * 4 * breadth, 4)
        assert _error_cost_robust(findings) == expected

    def test_breadth_cap_at_4(self) -> None:
        # With many related files, breadth should be capped at 4.0
        findings = [{
            "severity": "critical",
            "signal": "architecture_violation",
            "related_files": [f"f{i}.py" for i in range(200)],
        }]
        # 1 + ln(201) ≈ 6.3 → capped at 4.0
        # h=3.0, w_sev=8, breadth=4.0
        expected = round(3.0 * 8 * 4.0, 4)
        assert _error_cost_robust(findings) == expected

    def test_unknown_signal_uses_default_hours(self) -> None:
        findings = [{"severity": "medium", "signal": "unknown_signal_xyz"}]
        # h=1.0 (default), w_sev=2, breadth=1.0
        assert _error_cost_robust(findings) == round(1.0 * 2 * 1.0, 4)

    def test_signal_type_alias(self) -> None:
        """The function should accept 'signal_type' as fallback key."""
        findings = [{"severity": "high", "signal_type": "pattern_fragmentation"}]
        expected = round(2.0 * 4 * 1.0, 4)
        assert _error_cost_robust(findings) == expected

    def test_multiple_findings_additive(self) -> None:
        findings = [
            {"severity": "high", "signal": "pattern_fragmentation"},
            {"severity": "medium", "signal": "architecture_violation"},
        ]
        # f1: h=2.0, w=4, b=1.0 → 8.0
        # f2: h=3.0, w=2, b=1.0 → 6.0
        expected = round(8.0 + 6.0, 4)
        assert _error_cost_robust(findings) == expected


# ---------------------------------------------------------------------------
# _patch_line_count
# ---------------------------------------------------------------------------


class TestPatchLineCount:
    def test_empty_diff(self) -> None:
        assert _patch_line_count("") == 0

    def test_adds_and_removes(self) -> None:
        diff = (
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "@@ -1,3 +1,4 @@\n"
            " unchanged\n"
            "-removed_line\n"
            "+added_line_1\n"
            "+added_line_2\n"
            " unchanged\n"
        )
        # 1 removed + 2 added = 3 (headers --- +++ excluded)
        assert _patch_line_count(diff) == 3

    def test_header_lines_excluded(self) -> None:
        diff = "--- a/foo.py\n+++ b/foo.py\n"
        assert _patch_line_count(diff) == 0

    def test_only_additions(self) -> None:
        diff = (
            "--- a/f.py\n"
            "+++ b/f.py\n"
            "@@ -0,0 +1,2 @@\n"
            "+line1\n"
            "+line2\n"
        )
        assert _patch_line_count(diff) == 2

    def test_no_diff_headers(self) -> None:
        # Raw lines without --- +++ headers
        diff = "+added\n-removed\n context\n"
        assert _patch_line_count(diff) == 2


# ---------------------------------------------------------------------------
# _aggregate_by_task
# ---------------------------------------------------------------------------


class TestAggregateByTask:
    @staticmethod
    def _make_outcome(
        task_id: str,
        treatment: str,
        *,
        status: str = "ok",
        new_findings_count: float = 2.0,
        error_cost_default: float = 4.0,
        error_cost_robust: float = 8.0,
        net_cost_default: float = 2.0,
        net_cost_robust: float = 5.0,
        patch_size_loc: float = 10.0,
        accept_change: bool = True,
    ) -> dict[str, Any]:
        return {
            "task_id": task_id,
            "treatment": treatment,
            "status": status,
            "new_findings_count": new_findings_count,
            "error_cost_default": error_cost_default,
            "error_cost_robust": error_cost_robust,
            "net_cost_default": net_cost_default,
            "net_cost_robust": net_cost_robust,
            "patch_size_loc": patch_size_loc,
            "accept_change": accept_change,
        }

    def test_empty_outcomes(self) -> None:
        assert _aggregate_by_task([]) == {}

    def test_single_ok_run(self) -> None:
        outcomes = [self._make_outcome("T1", "control")]
        agg = _aggregate_by_task(outcomes)
        assert "T1" in agg
        assert "control" in agg["T1"]
        assert agg["T1"]["control"]["n_runs"] == 1.0
        assert agg["T1"]["control"]["new_findings_count"] == 2.0

    def test_multiple_repeats_averaged(self) -> None:
        outcomes = [
            self._make_outcome("T1", "control", error_cost_default=4.0),
            self._make_outcome("T1", "control", error_cost_default=8.0),
        ]
        agg = _aggregate_by_task(outcomes)
        assert agg["T1"]["control"]["n_runs"] == 2.0
        assert agg["T1"]["control"]["error_cost_default"] == 6.0  # (4+8)/2

    def test_non_ok_excluded(self) -> None:
        outcomes = [
            self._make_outcome("T1", "control"),
            self._make_outcome("T1", "control", status="error"),
        ]
        agg = _aggregate_by_task(outcomes)
        assert agg["T1"]["control"]["n_runs"] == 1.0

    def test_paired_tasks(self) -> None:
        outcomes = [
            self._make_outcome("T1", "control", error_cost_robust=10.0),
            self._make_outcome("T1", "treatment", error_cost_robust=5.0),
        ]
        agg = _aggregate_by_task(outcomes)
        assert "control" in agg["T1"]
        assert "treatment" in agg["T1"]
        assert agg["T1"]["control"]["error_cost_robust"] == 10.0
        assert agg["T1"]["treatment"]["error_cost_robust"] == 5.0

    def test_accept_rate(self) -> None:
        outcomes = [
            self._make_outcome("T1", "control", accept_change=True),
            self._make_outcome("T1", "control", accept_change=False),
        ]
        agg = _aggregate_by_task(outcomes)
        assert agg["T1"]["control"]["accept_rate"] == 0.5


# ---------------------------------------------------------------------------
# _SEVERITY_WEIGHTS completeness
# ---------------------------------------------------------------------------


class TestSeverityWeights:
    @pytest.mark.parametrize(
        "severity,expected",
        [
            ("critical", 8),
            ("high", 4),
            ("medium", 2),
            ("low", 1),
            ("info", 0),
        ],
    )
    def test_weight_values(self, severity: str, expected: int) -> None:
        assert _SEVERITY_WEIGHTS[severity] == expected

    def test_all_drift_severities_covered(self) -> None:
        expected_keys = {"critical", "high", "medium", "low", "info"}
        assert set(_SEVERITY_WEIGHTS.keys()) == expected_keys
