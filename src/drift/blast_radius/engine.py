"""Engine — orchestriert alle Analyzer zu einem ``BlastReport``.

Die Engine ist der einzige öffentliche Einstiegspunkt für Blast-Radius-Berechnungen.
Sie ist deterministisch (gleiches Repo + gleicher Diff → gleicher Report)
und garantiert, dass selbst bei einzelnen Analyzer-Fehlern ein valider
``BlastReport`` entsteht (``degraded=True`` + ``degradation_notes``).
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from drift.blast_radius._adr_analyzer import analyze_adr_impacts
from drift.blast_radius._arch_analyzer import analyze_arch_impacts
from drift.blast_radius._change_detector import detect_changes, resolve_repo_path
from drift.blast_radius._models import (
    BlastImpact,
    BlastImpactKind,
    BlastReport,
    BlastSeverity,
    BlastTrigger,
)
from drift.blast_radius._policy_analyzer import analyze_policy_impacts
from drift.blast_radius._skill_analyzer import analyze_skill_impacts

_log = logging.getLogger("drift.blast_radius.engine")

_SEVERITY_ORDER: dict[BlastSeverity, int] = {
    BlastSeverity.CRITICAL: 0,
    BlastSeverity.HIGH: 1,
    BlastSeverity.MEDIUM: 2,
    BlastSeverity.LOW: 3,
}


def _drift_version() -> str:
    try:
        from drift import __version__
    except ImportError:  # pragma: no cover — immer vorhanden
        return "unknown"
    return str(__version__)


def _sort_impacts(impacts: list[BlastImpact]) -> list[BlastImpact]:
    """Stabile Sortierung: Severity (critical zuerst), dann Kind, dann target_id."""
    return sorted(
        impacts,
        key=lambda imp: (
            _SEVERITY_ORDER.get(imp.severity, 99),
            imp.kind.value,
            imp.target_id,
        ),
    )


def _build_recommendations(impacts: list[BlastImpact]) -> list[str]:
    """Leite menschenlesbare Handlungsempfehlungen aus den Impacts ab."""
    recs: list[str] = []
    critical = [imp for imp in impacts if imp.requires_maintainer_ack]
    if critical:
        ids = ", ".join(sorted({imp.target_id for imp in critical}))
        recs.append(
            "Maintainer-Ack nötig für kritische Impacts: "
            f"{ids}. "
            "Lege blast_reports/acks/<short_sha>.yaml an (nur Maintainer)."
        )
    if any(imp.kind is BlastImpactKind.ADR for imp in impacts):
        recs.append(
            "Betroffene ADRs lesen und ggf. Status aktualisieren oder einen "
            "Supersedes-ADR entwerfen."
        )
    if any(imp.kind is BlastImpactKind.SKILL for imp in impacts):
        recs.append(
            "Guard-Skills re-validieren — applies_to-Patterns und Skill-Inhalt "
            "müssen konsistent mit der Änderung bleiben."
        )
    if any(imp.kind is BlastImpactKind.POLICY for imp in impacts):
        recs.append(
            "Audit-Artefakte unter audit_results/ aktualisieren, bevor der "
            "Push-Gate ausgeführt wird (Policy §18)."
        )
    if any(imp.kind is BlastImpactKind.ARCH_DEPENDENCY for imp in impacts):
        recs.append(
            "Abhängige Module mit pytest oder drift analyze gegenchecken, "
            "bevor gepusht wird."
        )
    return recs


def compute_blast_report(
    path: str | os.PathLike[str],
    *,
    ref: str = "HEAD",
    head: str = "HEAD",
    changed_files: list[str] | None = None,
    include_skills: bool = True,
    include_policy: bool = True,
) -> BlastReport:
    """Berechne einen ``BlastReport`` für den gegebenen Diff.

    Parameters
    ----------
    path:
        Repository-Root. Muss existieren.
    ref:
        Git-Basis-Referenz für den Diff (z. B. ``HEAD~1`` oder ``origin/main``).
    head:
        Git-HEAD (standardmäßig ``HEAD``; erlaubt Tests mit spezifischem SHA).
    changed_files:
        Optional expliziter Datei-Set, der Git-Diff ersetzt. POSIX-Pfade.
    include_skills:
        Wenn False, wird der Skill-Analyzer übersprungen.
    include_policy:
        Wenn False, wird der Policy-Analyzer übersprungen.

    Raises
    ------
    ValueError
        Wenn ``path`` nicht existiert.
    """
    repo_path = resolve_repo_path(path)
    changeset = detect_changes(
        repo_path,
        ref=ref,
        head=head,
        explicit_changed_files=changed_files,
    )

    impacts: list[BlastImpact] = []
    notes: list[str] = []

    # Arch — best-effort
    try:
        arch_impacts, arch_notes = analyze_arch_impacts(repo_path, changeset.changed_files)
    except Exception as exc:  # noqa: BLE001 — defensiv
        _log.exception("arch_analyzer fehlgeschlagen")
        arch_impacts = []
        arch_notes = [f"arch_analyzer Fehler: {exc.__class__.__name__}"]
    impacts.extend(arch_impacts)
    notes.extend(arch_notes)

    # ADR — best-effort
    try:
        adr_impacts, adr_notes = analyze_adr_impacts(repo_path, changeset.changed_files)
    except Exception as exc:  # noqa: BLE001
        _log.exception("adr_analyzer fehlgeschlagen")
        adr_impacts = []
        adr_notes = [f"adr_analyzer Fehler: {exc.__class__.__name__}"]
    impacts.extend(adr_impacts)
    notes.extend(adr_notes)

    if include_skills:
        try:
            skill_impacts, skill_notes = analyze_skill_impacts(
                repo_path, changeset.changed_files
            )
        except Exception as exc:  # noqa: BLE001
            _log.exception("skill_analyzer fehlgeschlagen")
            skill_impacts = []
            skill_notes = [f"skill_analyzer Fehler: {exc.__class__.__name__}"]
        impacts.extend(skill_impacts)
        notes.extend(skill_notes)

    if include_policy:
        try:
            policy_impacts, policy_notes = analyze_policy_impacts(
                repo_path, changeset.changed_files
            )
        except Exception as exc:  # noqa: BLE001
            _log.exception("policy_analyzer fehlgeschlagen")
            policy_impacts = []
            policy_notes = [f"policy_analyzer Fehler: {exc.__class__.__name__}"]
        impacts.extend(policy_impacts)
        notes.extend(policy_notes)

    sorted_impacts = _sort_impacts(impacts)
    recommendations = _build_recommendations(sorted_impacts)

    trigger = BlastTrigger(
        ref=changeset.ref,
        head=changeset.head,
        head_sha=changeset.head_sha,
        changed_files=changeset.changed_files,
    )
    generated_at = datetime.now(UTC).replace(microsecond=0).isoformat()
    generated_by = {
        "script": "drift.blast_radius.engine.compute_blast_report",
        "timestamp": generated_at,
        "git_sha": changeset.head_sha or "",
        "ref": changeset.ref,
        "head": changeset.head,
    }
    return BlastReport(
        generated_at=generated_at,
        drift_version=_drift_version(),
        trigger=trigger,
        impacts=tuple(sorted_impacts),
        recommendations=tuple(recommendations),
        degraded=bool(notes),
        degradation_notes=tuple(notes),
        generated_by=generated_by,
    )
