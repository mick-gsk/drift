"""Policy-Analyzer: triggert Pre-Push-Gate-Pflichten (§7, §18) als Blast-Impacts.

Der Analyzer ersetzt **nicht** die bestehenden Gates, sondern macht sie vor
dem Commit sichtbar, damit Agenten wissen, welche Audit-Artefakte sie
zusätzlich anfassen müssen.

Trigger-Regeln (abgeleitet aus ``.github/instructions/drift-push-gates.instructions.md``):

- Änderungen in ``src/drift/signals/**``, ``src/drift/ingestion/**``,
  ``src/drift/output/**`` → ``policy:risk_audit`` Impact (§7, §18).
- Änderungen in ``POLICY.md`` → ``policy:policy_update`` Impact (Maintainer-Review).
- Änderungen in ``src/drift/scoring/**`` → ``policy:scoring_change`` Impact.

Severity:

- ``high`` — benötigt Audit-Update, aber keine harte Ack.
- ``critical`` — POLICY.md-Änderungen; Ack-Pflicht.
"""

from __future__ import annotations

from pathlib import Path

from drift_engine.blast_radius._glob import files_matching
from drift_engine.blast_radius._models import BlastImpact, BlastImpactKind, BlastSeverity

_POLICY_RULES: tuple[tuple[str, tuple[str, ...], str, BlastSeverity, bool], ...] = (
    (
        "policy:risk_audit_signal",
        ("src/drift/signals/**",),
        (
            "Signal-Änderung erkannt — Pre-Push-Gate 7 (Risk-Audit) erfordert "
            "Aktualisierung von audit_results/fmea_matrix.md und risk_register.md."
        ),
        BlastSeverity.HIGH,
        False,
    ),
    (
        "policy:risk_audit_ingestion",
        ("src/drift/ingestion/**",),
        (
            "Ingestion-Änderung erkannt — Pre-Push-Gate 7 (Risk-Audit) erfordert "
            "Aktualisierung von audit_results/stride_threat_model.md."
        ),
        BlastSeverity.HIGH,
        False,
    ),
    (
        "policy:risk_audit_output",
        ("src/drift/output/**",),
        (
            "Output-Änderung erkannt — Pre-Push-Gate 7 (Risk-Audit) erfordert "
            "Aktualisierung von audit_results/fault_trees.md und fmea_matrix.md."
        ),
        BlastSeverity.HIGH,
        False,
    ),
    (
        "policy:scoring_change",
        ("src/drift/scoring/**",),
        (
            "Scoring-Änderung erkannt — Precision/Recall-Benchmarks und "
            "ADR-Referenz (Policy §13) müssen aktualisiert werden."
        ),
        BlastSeverity.HIGH,
        False,
    ),
    (
        "policy:policy_update",
        ("POLICY.md",),
        (
            "POLICY.md geändert — Maintainer-Review und Changelog-Eintrag sind "
            "Pflicht. Gate blockiert ohne Ack."
        ),
        BlastSeverity.CRITICAL,
        True,
    ),
)


def analyze_policy_impacts(
    repo_path: Path,  # noqa: ARG001 — reserviert für künftige Policy-Variante
    changed_files: tuple[str, ...],
) -> tuple[list[BlastImpact], list[str]]:
    """Leite Policy-Gate-Triggers aus dem Diff ab."""
    if not changed_files:
        return [], []
    impacts: list[BlastImpact] = []
    for target_id, patterns, reason, severity, requires_ack in _POLICY_RULES:
        matched: list[str] = []
        hit_pattern: str | None = None
        for pattern in patterns:
            candidates = files_matching(changed_files, pattern)
            if candidates:
                hit_pattern = pattern
                matched.extend(candidates)
        if not hit_pattern:
            continue
        impacts.append(
            BlastImpact(
                kind=BlastImpactKind.POLICY,
                target_id=target_id,
                target_path=None,
                severity=severity,
                reason=reason,
                scope_match=hit_pattern,
                matched_files=tuple(sorted(set(matched))),
                requires_maintainer_ack=requires_ack,
            )
        )
    return impacts, []
