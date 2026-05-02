"""Tests for compute_decision_status, compute_confidence, prioritize_risk_drivers (T007/T016)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from drift_cockpit._models import DecisionStatus
from drift_cockpit._status_engine import (
    compute_confidence,
    compute_decision_status,
    prioritize_risk_drivers,
)


def _finding(impact: float = 0.5, signal_id: str = "AVS") -> MagicMock:
    f = MagicMock(spec=["impact", "signal_id", "score", "score_contribution", "reason", "file", "severity"])
    f.impact = impact
    f.signal_id = signal_id
    f.score = impact
    f.score_contribution = impact
    f.reason = f"Finding for {signal_id}"
    f.file = None
    f.severity = "medium"
    return f


class TestComputeDecisionStatus:
    def test_go_at_threshold(self):
        assert compute_decision_status(0.85, has_evidence=True) == DecisionStatus.go

    def test_go_above_threshold(self):
        assert compute_decision_status(1.0, has_evidence=True) == DecisionStatus.go

    def test_guardrails_at_boundary(self):
        assert compute_decision_status(0.60, has_evidence=True) == DecisionStatus.go_with_guardrails

    def test_guardrails_mid(self):
        assert compute_decision_status(0.72, has_evidence=True) == DecisionStatus.go_with_guardrails

    def test_no_go_below_threshold(self):
        assert compute_decision_status(0.59, has_evidence=True) == DecisionStatus.no_go

    def test_no_go_zero(self):
        assert compute_decision_status(0.0, has_evidence=True) == DecisionStatus.no_go

    def test_no_evidence_forces_no_go(self):
        # Even high confidence → no_go if no evidence
        assert compute_decision_status(0.99, has_evidence=False) == DecisionStatus.no_go


class TestComputeConfidence:
    def test_no_findings_is_full_confidence(self):
        assert compute_confidence([]) == pytest.approx(1.0)

    def test_high_impact_reduces_confidence(self):
        findings = [_finding(impact=0.9)]
        assert compute_confidence(findings) < 1.0

    def test_confidence_bounded_zero_one(self):
        findings = [_finding(impact=1.0)] * 5
        c = compute_confidence(findings)
        assert 0.0 <= c <= 1.0


class TestPrioritizeRiskDrivers:
    def test_sorted_by_impact_desc(self):
        f1 = _finding(impact=0.3, signal_id="AVS")
        f2 = _finding(impact=0.8, signal_id="PFS")
        f3 = _finding(impact=0.1, signal_id="MDS")
        drivers = prioritize_risk_drivers([f1, f2, f3])
        assert drivers[0].impact >= drivers[1].impact >= drivers[2].impact

    def test_empty_findings(self):
        assert prioritize_risk_drivers([]) == []
