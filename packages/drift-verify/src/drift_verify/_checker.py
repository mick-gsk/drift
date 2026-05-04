"""Deterministic analysis layer — wraps drift analyze Python API (AVS/PFS/EDS)."""

from __future__ import annotations

import logging
from pathlib import Path

from drift_verify._models import (
    ActionRecommendation,
    ChangeSet,
    EvidenceFlag,
    IndependentReviewResult,
    Severity,
    Verdict,
    ViolationFinding,
    ViolationType,
)

_log = logging.getLogger(__name__)

_SIGNAL_TO_VIOLATION: dict[str, ViolationType] = {
    "AVS": ViolationType.layer_violation,
    "EDS": ViolationType.forbidden_dependency,
    "PFS": ViolationType.file_placement,
    "MDS": ViolationType.naming_convention,
}

_SEVERITY_MAP: dict[str, Severity] = {
    "critical": Severity.critical,
    "high": Severity.high,
    "medium": Severity.medium,
    "low": Severity.low,
    "info": Severity.low,
}

_REMEDIATION_TEMPLATES: dict[ViolationType, str] = {
    ViolationType.layer_violation: (
        "Move or refactor this change to respect layer boundaries. "
        "Upper layers must not be imported by lower layers."
    ),
    ViolationType.forbidden_dependency: (
        "Remove the forbidden import/dependency. "
        "Check drift.yaml for allowed dependency rules."
    ),
    ViolationType.file_placement: (
        "Move the file to the correct location as defined by the project structure. "
        "See drift.yaml file_placement rules."
    ),
    ViolationType.naming_convention: (
        "Rename to follow the project naming convention. "
        "See drift.yaml naming rules."
    ),
    ViolationType.rule_conflict: (
        "Resolve the conflicting rules manually. "
        "Two rules produce contradicting verdicts for this file."
    ),
}


def _severity_from_str(s: str | None) -> Severity:
    return _SEVERITY_MAP.get((s or "").lower(), Severity.medium)


def map_signal_finding_to_violation(finding: object) -> ViolationFinding:
    """Map a drift signal Finding to a ViolationFinding."""
    signal_id: str = getattr(finding, "signal_id", "") or ""
    vtype = _SIGNAL_TO_VIOLATION.get(signal_id, ViolationType.layer_violation)
    severity = _severity_from_str(getattr(finding, "severity", None))
    file_val: str | None = getattr(finding, "file", None)
    line_val: int | None = getattr(finding, "line", None)
    message: str = getattr(finding, "message", str(finding))
    remediation = _REMEDIATION_TEMPLATES.get(
        vtype,
        _REMEDIATION_TEMPLATES[ViolationType.layer_violation],
    )
    return ViolationFinding(
        violation_type=vtype,
        severity=severity,
        file=file_val,
        line=line_val,
        rule_id=signal_id or None,
        message=message,
        remediation=remediation,
    )


def run_deterministic_checks(
    change_set: ChangeSet,
) -> tuple[list[ViolationFinding], set[EvidenceFlag]]:
    """Run drift analyze over changed files; return (violations, flags)."""
    flags: set[EvidenceFlag] = set()
    violations: list[ViolationFinding] = []

    changed = list(change_set.changed_files)
    if not change_set.diff_text.strip() and not changed:
        flags.add(EvidenceFlag.no_changes_detected)
        return violations, flags

    try:
        from drift_engine.analyzer import DriftAnalyzer  # type: ignore[import-untyped]

        analyzer = DriftAnalyzer(repo_path=change_set.repo_path)
        result = analyzer.analyze(file_paths=changed if changed else None)
        raw_findings = getattr(result, "findings", [])
        for f in raw_findings:
            violations.append(map_signal_finding_to_violation(f))
    except Exception as exc:  # noqa: BLE001
        _log.debug("drift_engine.analyzer unavailable: %s — no violations", exc)

    # Detect rule conflicts: same file with two different signal verdicts
    file_signals: dict[str | None, list[str]] = {}
    for v in violations:
        file_signals.setdefault(v.file, []).append(v.rule_id or "")
    for file, sigs in file_signals.items():
        if len(set(sigs)) > 1:
            flags.add(EvidenceFlag.rule_conflict)
            conflict = ViolationFinding(
                violation_type=ViolationType.rule_conflict,
                severity=Severity.high,
                file=file,
                rule_id=sigs[0],
                conflicting_rule_id=sigs[1],
                message=f"Rule conflict between {sigs[0]} and {sigs[1]} for {file}",
                remediation=_REMEDIATION_TEMPLATES[ViolationType.rule_conflict],
            )
            violations.append(conflict)

    return violations, flags


def compute_drift_score(violations: list[ViolationFinding]) -> float:
    """Compute drift score in [0.0, 1.0] from violations (pure function)."""
    if not violations:
        return 0.0
    severity_weights = {
        Severity.critical: 1.0,
        Severity.high: 0.75,
        Severity.medium: 0.5,
        Severity.low: 0.25,
    }
    total = sum(severity_weights[v.severity] for v in violations)
    # Normalise: cap at 1.0 (5 high-severity = 1.0)
    return min(1.0, total / 5.0)


def compute_spec_confidence(
    change_set: ChangeSet,
    violations: list[ViolationFinding],
) -> float:
    """Compute spec confidence score (passed_checks / total_checks), pure function."""
    spec_path = change_set.spec_path
    if spec_path is None or not Path(spec_path).exists():
        # No spec: base confidence on absence of violations
        return 1.0 if not violations else max(0.0, 1.0 - len(violations) * 0.1)

    # Count acceptance criteria lines in spec (lines starting with "- ")
    try:
        spec_text = Path(spec_path).read_text(encoding="utf-8")
    except OSError:
        return 1.0 if not violations else max(0.0, 1.0 - len(violations) * 0.1)

    criteria = [
        ln
        for ln in spec_text.splitlines()
        if ln.strip().startswith("- ") and any(
            kw in ln.lower()
            for kw in ("must", "shall", "should", "given", "when", "then")
        )
    ]
    total = len(criteria) if criteria else 10
    failed = min(len(violations), total)
    return max(0.0, (total - failed) / total)


def build_action_recommendation(
    drift_score: float,
    spec_confidence: float,
    violations: list[ViolationFinding],
    flags: set[EvidenceFlag],
    *,
    threshold_drift: float = 0.2,
    threshold_confidence: float = 0.8,
    independent_review: IndependentReviewResult | None = None,
) -> ActionRecommendation:
    """Build ActionRecommendation — pure function, deterministic logic."""
    if EvidenceFlag.no_changes_detected in flags:
        return ActionRecommendation(
            verdict=Verdict.automerge,
            reason="No changes detected in diff.",
            blocking_violation_count=0,
        )

    blocking = [
        v
        for v in violations
        if v.severity in (Severity.critical, Severity.high)
        and v.violation_type != ViolationType.rule_conflict
    ]

    if EvidenceFlag.rule_conflict in flags:
        return ActionRecommendation(
            verdict=Verdict.needs_review,
            reason="Rule conflict detected — manual review required.",
            blocking_violation_count=len(blocking),
        )

    if blocking:
        return ActionRecommendation(
            verdict=Verdict.needs_fix,
            reason=f"{len(blocking)} blocking violation(s) with high/critical severity.",
            blocking_violation_count=len(blocking),
        )

    if (
        independent_review is not None
        and not independent_review.available
        and len(violations) > 0
    ):
        return ActionRecommendation(
            verdict=Verdict.needs_review,
            reason="Independent review unavailable; non-empty violations present.",
            blocking_violation_count=0,
        )

    if (
        drift_score <= threshold_drift
        and spec_confidence >= threshold_confidence
        and not violations
    ):
        return ActionRecommendation(
            verdict=Verdict.automerge,
            reason="Drift score and spec confidence within thresholds; no violations.",
            blocking_violation_count=0,
        )

    return ActionRecommendation(
        verdict=Verdict.needs_review,
        reason="Non-blocking violations or threshold not met.",
        blocking_violation_count=0,
    )
