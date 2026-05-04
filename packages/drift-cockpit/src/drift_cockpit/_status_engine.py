"""Decision status engine for drift-cockpit (Feature 006).

All functions are pure — no I/O, no side effects.
Thresholds are fixed per FR-012.
"""

from __future__ import annotations

from drift_sdk.models import Finding

from drift_cockpit._models import DecisionStatus, RiskDriver

# ---------------------------------------------------------------------------
# Fixed confidence thresholds (FR-012)
# Note: boundary value goes to the LOWER status (no_go wins at 0.60, etc.)
# ---------------------------------------------------------------------------
_THRESHOLD_GO: float = 0.85         # confidence >= 0.85 → go
_THRESHOLD_GUARDRAILS: float = 0.60  # 0.60 <= confidence < 0.85 → go_with_guardrails
                                     # confidence < 0.60 → no_go


def compute_decision_status(confidence: float, *, has_evidence: bool) -> DecisionStatus:
    """Map a confidence score to exactly one DecisionStatus (FR-001, FR-011, FR-012).

    Missing evidence always returns no_go regardless of confidence.
    Boundary values map to the lower status (no_go wins at exact boundaries).
    """
    if not has_evidence:
        return DecisionStatus.no_go
    if confidence >= _THRESHOLD_GO:
        return DecisionStatus.go
    if confidence >= _THRESHOLD_GUARDRAILS:
        return DecisionStatus.go_with_guardrails
    return DecisionStatus.no_go


def compute_confidence(findings: list[Finding]) -> float:
    """Derive a confidence score in [0.0, 1.0] from signal findings.

    Confidence = 1.0 - normalised aggregate impact.
    No findings → confidence 1.0 (clean).
    """
    if not findings:
        return 1.0
    # Sum impact; each finding's impact is in [0.0, 1.0].
    total_impact = sum(getattr(f, "impact", 0.0) for f in findings)
    # Normalise with a soft cap: at total_impact==len(findings) confidence→0.
    max_possible = max(len(findings), 1)
    normalised = min(total_impact / max_possible, 1.0)
    return round(max(0.0, 1.0 - normalised), 4)


def compute_risk_score(findings: list[Finding]) -> float:
    """Derive an aggregate risk score in [0.0, 1.0]."""
    if not findings:
        return 0.0
    total = sum(getattr(f, "score", 0.0) for f in findings)
    return round(min(total / max(len(findings), 1), 1.0), 4)


def prioritize_risk_drivers(findings: list[Finding]) -> list[RiskDriver]:
    """Convert signal findings to sorted RiskDrivers (FR-002).

    Sorted by impact descending (highest impact driver first).
    """
    drivers: list[RiskDriver] = []
    for f in findings:
        impact = getattr(f, "impact", 0.0)
        severity_val = getattr(f, "severity", None)
        severity_str = (
            severity_val.value if hasattr(severity_val, "value") else str(severity_val or "medium")
        )
        signal_id = getattr(f, "signal_id", None) or getattr(f, "check", None) or "unknown"
        file_ref = getattr(f, "file", None) or getattr(f, "path", None)
        drivers.append(
            RiskDriver(
                driver_id=str(id(f)),
                title=getattr(f, "reason", signal_id),
                impact=impact,
                severity=severity_str,
                source_refs=[str(file_ref)] if file_ref else [],
            )
        )
    return sorted(drivers, key=lambda d: d.impact, reverse=True)
