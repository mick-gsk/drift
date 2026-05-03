"""Kerntests für die Blast-Radius-Engine (ADR-087).

Fokus: Analyzer-Kontrakte, Engine-Verhalten bei Triggern, Policy-Critical-Ack
und Persistenz-Roundtrip. Keine Git-Integration (wird via ``changed_files``
override umgangen), keine MCP-Router-Tests (siehe ``test_blast_radius_mcp``).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from drift.blast_radius import (
    BlastReport,
    BlastSeverity,
    compute_blast_report,
    load_blast_report,
    save_blast_report,
)
from drift.blast_radius._adr_analyzer import analyze_adr_impacts
from drift.blast_radius._policy_analyzer import analyze_policy_impacts
from drift.blast_radius._skill_analyzer import analyze_skill_impacts


@pytest.fixture
def repo_root() -> Path:
    """Drift-Repository-Root (Eltern von ``packages/drift/src/drift``)."""

    path = Path(__file__).resolve().parents[1]
    # After ADR-100 monorepo migration, src/drift was removed.  The meta-package
    # at packages/drift/src/drift (re-export stubs) serves as a stable marker
    # that the repo root was resolved correctly.
    assert (path / "packages" / "drift" / "src" / "drift").is_dir(), (
        "Repo-Root falsch aufgelöst."
    )
    return path


def test_policy_md_change_is_critical_with_ack(repo_root: Path) -> None:
    impacts, _notes = analyze_policy_impacts(repo_root, ("POLICY.md",))
    assert impacts, "POLICY.md muss Policy-Impacts erzeugen."
    critical = [i for i in impacts if i.severity == BlastSeverity.CRITICAL]
    assert critical, "POLICY.md → mindestens ein CRITICAL-Impact erwartet."
    assert all(i.requires_maintainer_ack for i in critical)


def test_signals_change_triggers_high_policy_impact(repo_root: Path) -> None:
    impacts, _notes = analyze_policy_impacts(
        repo_root, ("src/drift/signals/pfs.py",)
    )
    kinds = {(i.target_id, i.severity) for i in impacts}
    assert any(sev == BlastSeverity.HIGH for _tid, sev in kinds), (
        "Signal-Änderung muss HIGH-Policy-Impact triggern."
    )


def test_skill_analyzer_matches_guard_skills(repo_root: Path) -> None:
    impacts, _notes = analyze_skill_impacts(
        repo_root, ("src/drift/signals/pfs.py",)
    )
    target_ids = {i.target_id for i in impacts}
    # Erwartet zumindest den Signal-spezifischen Guard oder den globalen Guard
    assert any("guard-src-drift" in tid for tid in target_ids), (
        f"Erwarte Guard-Skill-Match, bekam: {target_ids}"
    )


def test_adr_text_fallback_finds_matching_adrs(repo_root: Path) -> None:
    # ADR-087 selbst sollte zumindest via Text-Fallback gematcht werden,
    # wenn der eigene Pfad geändert wird.
    impacts, _notes = analyze_adr_impacts(
        repo_root, ("src/drift/blast_radius/engine.py",)
    )
    assert any(i.target_id.startswith("ADR-") for i in impacts), (
        "Erwarte mindestens einen ADR-Match (strukturiert oder Text-Fallback)."
    )


def test_engine_returns_frozen_report_with_sorted_impacts(
    repo_root: Path,
) -> None:
    report = compute_blast_report(
        repo_root,
        changed_files=["POLICY.md", "src/drift/signals/pfs.py"],
    )
    assert isinstance(report, BlastReport)
    assert report.schema_v == 1
    # Immutable: frozen Pydantic-Modelle werfen ValidationError bei Attribut-Set
    from pydantic import ValidationError

    with pytest.raises((ValidationError, TypeError, AttributeError)):
        report.schema_v = 2  # type: ignore[misc]
    # Severities absteigend
    severities = [i.severity for i in report.impacts]
    order = {
        BlastSeverity.CRITICAL: 0,
        BlastSeverity.HIGH: 1,
        BlastSeverity.MEDIUM: 2,
        BlastSeverity.LOW: 3,
    }
    ordinals = [order[s] for s in severities]
    assert ordinals == sorted(ordinals), (
        f"Impacts müssen nach Severity sortiert sein: {severities}"
    )


def test_engine_no_triggers_yields_empty_report(repo_root: Path) -> None:
    report = compute_blast_report(
        repo_root, changed_files=["README.md"]
    )
    # README triggert keine Policy/Skill/ADR-Regel → keine Critical-Ack nötig
    assert not report.has_critical_impacts()


def test_persistence_roundtrip(tmp_path: Path, repo_root: Path) -> None:
    report = compute_blast_report(
        repo_root, changed_files=["src/drift/signals/pfs.py"]
    )
    target = save_blast_report(tmp_path, report)
    assert target.exists()
    assert target.parent.name == "blast_reports"
    loaded = load_blast_report(target)
    assert loaded.schema_v == report.schema_v
    assert len(loaded.impacts) == len(report.impacts)


def test_disabling_skills_and_policy_reduces_impacts(repo_root: Path) -> None:
    full = compute_blast_report(
        repo_root, changed_files=["src/drift/signals/pfs.py"]
    )
    minimal = compute_blast_report(
        repo_root,
        changed_files=["src/drift/signals/pfs.py"],
        include_skills=False,
        include_policy=False,
    )
    assert len(minimal.impacts) < len(full.impacts)
