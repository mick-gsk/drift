"""Minimal Safe Change Set computation for drift-cockpit (Feature 006).

Pure functions — no I/O.
"""

from __future__ import annotations

import uuid

from drift_sdk.models import Finding

from drift_cockpit._models import (
    DecisionBundle,
    DecisionStatus,
    GuardrailCondition,
    MinimalSafePlan,
)


def _make_guardrail_from_finding(finding: Finding) -> GuardrailCondition:
    signal_id = getattr(finding, "signal_id", None) or getattr(finding, "check", None) or "unknown"
    file_ref = getattr(finding, "file", None) or getattr(finding, "path", None)
    location = f" in `{file_ref}`" if file_ref else ""
    return GuardrailCondition(
        condition_id=f"gc-{uuid.uuid4().hex[:8]}",
        description=getattr(finding, "reason", f"Resolve {signal_id}{location}"),
        verification_method="Re-run `drift analyze` and confirm finding is absent",
        must_pass_before_merge=True,
    )


def compute_expected_deltas(
    current_score: float,
    target_threshold: float,
    findings_to_fix: list[Finding],
) -> tuple[float, float]:
    """Return (risk_delta, score_delta) for resolving a set of findings.

    risk_delta < 0 means risk reduction.
    score_delta > 0 means score improvement.
    """
    impact_sum = sum(getattr(f, "impact", 0.0) for f in findings_to_fix)
    risk_delta = round(-impact_sum / max(len(findings_to_fix), 1), 4)
    score_gain = max(0.0, target_threshold - current_score + 0.01)
    score_delta = round(min(score_gain, 1.0 - current_score), 4)
    return risk_delta, score_delta


def compute_safe_plans(
    bundle: DecisionBundle,
    findings: list[Finding],
) -> list[MinimalSafePlan]:
    """Compute the minimal safe change sets for a given bundle (FR-003/FR-004).

    Returns empty list for go status.
    No-go and guardrails each get one plan covering the highest-impact findings.
    """
    if bundle.status == DecisionStatus.go:
        return []

    if not findings:
        return []

    # Sort findings by impact descending; take the highest-impact ones
    sorted_findings = sorted(findings, key=lambda f: getattr(f, "impact", 0.0), reverse=True)

    # Target threshold depends on status
    target_threshold = 0.60 if bundle.status == DecisionStatus.no_go else 0.85

    # Greedy minimal cover: take top-N findings that together cover the gap
    current_confidence = bundle.confidence
    selected: list[Finding] = []
    running_impact = 0.0
    needed_gain = max(0.0, target_threshold - current_confidence)

    for f in sorted_findings:
        if running_impact >= needed_gain and selected:
            break
        selected.append(f)
        max_len = max(len(selected), 1)
        running_impact += getattr(f, "impact", 0.0) / max_len

    risk_delta, score_delta = compute_expected_deltas(
        current_confidence, target_threshold, selected
    )
    conditions = [_make_guardrail_from_finding(f) for f in selected]

    plan = MinimalSafePlan(
        plan_id=f"msp-{uuid.uuid4().hex[:8]}",
        pr_id=bundle.pr_id,
        steps=conditions,
        expected_risk_delta=risk_delta,
        expected_score_delta=score_delta,
        target_threshold=target_threshold,
        feasible=True,
    )
    return [plan]
