"""Parametrized threshold boundary tests for drift-cockpit (T007/T016)."""

from __future__ import annotations

import pytest
from drift_cockpit._models import DecisionStatus
from drift_cockpit._status_engine import compute_decision_status


@pytest.mark.parametrize(
    "confidence, expected",
    [
        (0.849999, DecisionStatus.go_with_guardrails),  # just below go threshold
        (0.850000, DecisionStatus.go),                  # exactly at go threshold
        (0.599999, DecisionStatus.no_go),               # just below guardrails threshold
        (0.600000, DecisionStatus.go_with_guardrails),  # exactly at guardrails threshold
        (1.000000, DecisionStatus.go),                  # maximum
        (0.000000, DecisionStatus.no_go),               # minimum
    ],
)
def test_threshold_boundary(confidence: float, expected: DecisionStatus) -> None:
    assert compute_decision_status(confidence, has_evidence=True) == expected


def test_no_evidence_override() -> None:
    """Evidence absence always overrides confidence (FR-011)."""
    for confidence in (0.0, 0.60, 0.85, 1.0):
        assert (
            compute_decision_status(confidence, has_evidence=False) == DecisionStatus.no_go
        ), f"Expected no_go for confidence={confidence} with no evidence"
