"""drift-cockpit: Human Decision Cockpit for drift-analyzer (Feature 006).

Public API:
    build_decision_bundle(pr_id, findings) -> DecisionBundle
"""

from __future__ import annotations

from drift_sdk.models import Finding

from drift_cockpit._cluster import aggregate_clusters
from drift_cockpit._exceptions import (
    MissingEvidenceError,
    MissingOverrideJustificationError,
    VersionConflictError,
)
from drift_cockpit._models import (
    AccountabilityCluster,
    DecisionBundle,
    DecisionStatus,
    GuardrailCondition,
    LedgerEntry,
    MinimalSafePlan,
    OutcomeSnapshot,
    OutcomeState,
    RiskDriver,
)
from drift_cockpit._safe_plan import compute_safe_plans
from drift_cockpit._status_engine import (
    compute_confidence,
    compute_decision_status,
    compute_risk_score,
    prioritize_risk_drivers,
)

__all__ = [
    # Public entry point
    "build_decision_bundle",
    # Models
    "AccountabilityCluster",
    "DecisionBundle",
    "DecisionStatus",
    "GuardrailCondition",
    "LedgerEntry",
    "MinimalSafePlan",
    "OutcomeSnapshot",
    "OutcomeState",
    "RiskDriver",
    # Exceptions
    "MissingEvidenceError",
    "MissingOverrideJustificationError",
    "VersionConflictError",
]


def build_decision_bundle(
    pr_id: str,
    findings: list[Finding],
    *,
    prior_version: int | None = None,
) -> DecisionBundle:
    """Build a complete DecisionBundle for a given PR (FR-001..FR-012).

    Parameters
    ----------
    pr_id:
        Unique identifier for the Pull Request.
    findings:
        Signal findings from drift analysis. Empty list → no_go (FR-011).
    prior_version:
        Previous bundle version if available; next version = prior_version + 1.

    Raises
    ------
    MissingEvidenceError
        When findings is empty. Status is set to no_go before raising if caller
        needs the bundle despite missing evidence, pass findings=[].
        Note: the error is informational — callers that want a no_go bundle
        for an evidence-less PR may catch this and use a fallback bundle.
    """
    has_evidence = bool(findings)
    confidence = compute_confidence(findings) if has_evidence else 0.0
    risk_score = compute_risk_score(findings) if has_evidence else 0.0
    status = compute_decision_status(confidence, has_evidence=has_evidence)
    risk_drivers = prioritize_risk_drivers(findings)

    version = (prior_version + 1) if prior_version is not None else 1

    # Build a preliminary bundle to pass to safe_plan / cluster computations
    partial = DecisionBundle(
        pr_id=pr_id,
        status=status,
        confidence=confidence,
        evidence_sufficient=has_evidence,
        risk_score=risk_score,
        top_risk_drivers=risk_drivers,
        version=version,
    )

    safe_plans = compute_safe_plans(partial, findings)

    raw_clusters = aggregate_clusters(findings)
    clusters = [
        AccountabilityCluster(
            cluster_id=c.cluster_id,
            pr_id=pr_id,
            label=c.label,
            files=c.files,
            risk_contribution=c.risk_contribution,
            dominant_drivers=c.dominant_drivers,
        )
        for c in raw_clusters
    ]

    bundle = DecisionBundle(
        pr_id=pr_id,
        status=status,
        confidence=confidence,
        evidence_sufficient=has_evidence,
        risk_score=risk_score,
        top_risk_drivers=risk_drivers,
        safe_plans=safe_plans,
        risk_clusters=clusters,
        version=version,
    )

    if not has_evidence:
        raise MissingEvidenceError(pr_id)

    return bundle
