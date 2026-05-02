"""Tests for compute_safe_plans and compute_expected_deltas (T007/T022)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from drift_cockpit._models import DecisionBundle, DecisionStatus
from drift_cockpit._safe_plan import compute_expected_deltas, compute_safe_plans


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


def _bundle(status: DecisionStatus, confidence: float = 0.5) -> DecisionBundle:
    return DecisionBundle(
        pr_id="PR-1",
        status=status,
        confidence=confidence,
        evidence_sufficient=True,
        risk_score=1.0 - confidence,
        version=1,
    )


class TestComputeSafePlans:
    def test_go_returns_empty(self):
        bundle = _bundle(DecisionStatus.go, confidence=0.90)
        plans = compute_safe_plans(bundle, [_finding()])
        assert plans == []

    def test_no_go_returns_plans(self):
        bundle = _bundle(DecisionStatus.no_go, confidence=0.40)
        findings = [_finding(impact=0.6, signal_id="AVS")]
        plans = compute_safe_plans(bundle, findings)
        assert len(plans) >= 1

    def test_guardrails_returns_plans(self):
        bundle = _bundle(DecisionStatus.go_with_guardrails, confidence=0.70)
        findings = [_finding(impact=0.3, signal_id="PFS")]
        plans = compute_safe_plans(bundle, findings)
        assert len(plans) >= 1

    def test_no_findings_with_no_go_empty_plans(self):
        bundle = _bundle(DecisionStatus.no_go, confidence=0.0)
        plans = compute_safe_plans(bundle, [])
        assert plans == []


class TestComputeExpectedDeltas:
    def test_delta_sign_correct(self):
        findings = [_finding(impact=0.3)]
        risk_delta, score_delta = compute_expected_deltas(0.4, 0.60, findings)
        # Fixing findings should decrease risk and increase score
        assert risk_delta < 0 or risk_delta == pytest.approx(0.0)
        assert score_delta >= 0 or score_delta == pytest.approx(0.0)

    def test_current_above_target_zero_deltas(self):
        """If already above threshold, no delta needed."""
        risk_delta, score_delta = compute_expected_deltas(0.90, 0.85, [])
        assert risk_delta == pytest.approx(0.0)
        assert score_delta == pytest.approx(0.0)
