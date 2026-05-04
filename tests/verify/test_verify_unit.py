"""Unit tests for drift-verify: models, checker, promoter (TDD Red phase → Green)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from drift_verify._checker import (
    build_action_recommendation,
    compute_drift_score,
    compute_spec_confidence,
)
from drift_verify._models import (
    ActionRecommendation,
    ChangeSet,
    EvidenceFlag,
    EvidencePackage,
    FunctionalEvidence,
    PatternHistoryEntry,
    Severity,
    Verdict,
    ViolationFinding,
    ViolationType,
    compute_change_set_id,
)
from drift_verify._promoter import (
    compute_promotions,
)
from drift_verify._reviewer import MockReviewerAgent
from drift_verify._verify import verify

# ---------------------------------------------------------------------------
# T006 — Model invariants
# ---------------------------------------------------------------------------

class TestModels:
    def test_evidence_package_score_range_valid(self) -> None:
        pkg = _make_package(drift_score=0.5, spec_confidence=0.9)
        assert 0.0 <= pkg.drift_score <= 1.0
        assert 0.0 <= pkg.spec_confidence_score <= 1.0

    def test_evidence_package_score_out_of_range(self) -> None:
        with pytest.raises(Exception):
            _make_package(drift_score=1.5)

    def test_no_changes_flag_requires_empty_violations(self) -> None:
        with pytest.raises(Exception):
            EvidencePackage(
                **{"schema": "evidence-package-v1"},
                version="0",
                change_set_id="empty",
                repo=".",
                verified_at=datetime.now(tz=UTC),
                drift_score=0.0,
                spec_confidence_score=1.0,
                action_recommendation=ActionRecommendation(
                    verdict=Verdict.automerge,
                    reason="no changes",
                ),
                violations=[
                    ViolationFinding(
                        violation_type=ViolationType.layer_violation,
                        severity=Severity.low,
                        message="x",
                        remediation="y",
                    )
                ],
                flags=frozenset({EvidenceFlag.no_changes_detected}),
            )

    def test_rule_conflict_violation_requires_conflicting_id(self) -> None:
        with pytest.raises(Exception):
            ViolationFinding(
                violation_type=ViolationType.rule_conflict,
                severity=Severity.high,
                message="conflict",
                remediation="fix",
                # conflicting_rule_id omitted — must raise
            )

    def test_rule_conflict_violation_ok_with_both_ids(self) -> None:
        v = ViolationFinding(
            violation_type=ViolationType.rule_conflict,
            severity=Severity.high,
            message="conflict",
            remediation="fix",
            rule_id="AVS",
            conflicting_rule_id="EDS",
        )
        assert v.conflicting_rule_id == "EDS"

    def test_compute_change_set_id_empty(self) -> None:
        assert compute_change_set_id("") == "empty"
        assert compute_change_set_id("  \n  ") == "empty"

    def test_compute_change_set_id_deterministic(self) -> None:
        id1 = compute_change_set_id("diff text")
        id2 = compute_change_set_id("diff text")
        assert id1 == id2

    def test_evidence_package_frozen(self) -> None:
        pkg = _make_package()
        with pytest.raises(Exception):
            pkg.drift_score = 0.99  # type: ignore[misc]


# ---------------------------------------------------------------------------
# T014 — compute_drift_score
# ---------------------------------------------------------------------------

class TestDriftScore:
    def test_no_violations_gives_zero(self) -> None:
        assert compute_drift_score([]) == 0.0

    def test_single_critical_gives_max_normalised(self) -> None:
        v = _violation(Severity.critical)
        score = compute_drift_score([v])
        assert score == 1.0 / 5.0

    def test_five_high_gives_one(self) -> None:
        vs = [_violation(Severity.high) for _ in range(7)]  # 7 * 0.75 = 5.25 → capped at 1.0
        score = compute_drift_score(vs)
        assert score == pytest.approx(1.0)

    def test_score_capped_at_one(self) -> None:
        vs = [_violation(Severity.critical) for _ in range(10)]
        assert compute_drift_score(vs) == 1.0


# ---------------------------------------------------------------------------
# T015 — compute_spec_confidence
# ---------------------------------------------------------------------------

class TestSpecConfidence:
    def test_no_violations_no_spec_gives_one(self, tmp_path: Path) -> None:
        cs = ChangeSet(repo_path=tmp_path)
        score = compute_spec_confidence(cs, [])
        assert score == 1.0

    def test_violations_reduce_confidence(self, tmp_path: Path) -> None:
        cs = ChangeSet(repo_path=tmp_path)
        violations = [_violation(Severity.medium) for _ in range(3)]
        score = compute_spec_confidence(cs, violations)
        assert score < 1.0


# ---------------------------------------------------------------------------
# T016 — build_action_recommendation
# ---------------------------------------------------------------------------

class TestActionRecommendation:
    def test_no_changes_gives_automerge(self) -> None:
        rec = build_action_recommendation(
            0.0, 1.0, [], {EvidenceFlag.no_changes_detected}
        )
        assert rec.verdict == Verdict.automerge

    def test_critical_violation_gives_needs_fix(self) -> None:
        v = _violation(Severity.critical)
        rec = build_action_recommendation(0.8, 0.3, [v], set())
        assert rec.verdict == Verdict.needs_fix

    def test_high_violation_gives_needs_fix(self) -> None:
        v = _violation(Severity.high)
        rec = build_action_recommendation(0.6, 0.5, [v], set())
        assert rec.verdict == Verdict.needs_fix

    def test_rule_conflict_overrides_to_needs_review(self) -> None:
        rec = build_action_recommendation(
            0.0, 1.0, [], {EvidenceFlag.rule_conflict}
        )
        assert rec.verdict == Verdict.needs_review

    def test_clean_diff_gives_automerge(self) -> None:
        rec = build_action_recommendation(0.1, 0.9, [], set())
        assert rec.verdict == Verdict.automerge

    def test_medium_violations_give_needs_review(self) -> None:
        v = _violation(Severity.medium)
        rec = build_action_recommendation(0.3, 0.7, [v], set())
        assert rec.verdict == Verdict.needs_review


# ---------------------------------------------------------------------------
# T020 / T022 — US1: verify() API
# ---------------------------------------------------------------------------

class TestVerifyAPI:
    def test_empty_diff_automerge(self, tmp_path: Path) -> None:
        cs = ChangeSet(diff_text="", repo_path=tmp_path)
        pkg = verify(
            cs,
            use_reviewer=False,
            history_store=_null_store(tmp_path),
        )
        assert EvidenceFlag.no_changes_detected in pkg.flags
        assert pkg.action_recommendation.verdict == Verdict.automerge
        assert pkg.drift_score == 0.0
        assert pkg.spec_confidence_score == 1.0
        assert pkg.violations == []

    def test_package_reproducible(self, tmp_path: Path) -> None:
        cs = ChangeSet(diff_text="--- a\n+++ b\n@@ -1,1 +1,1 @@\n-x\n+y", repo_path=tmp_path)
        pkg1 = verify(cs, use_reviewer=False, history_store=_null_store(tmp_path))
        pkg2 = verify(cs, use_reviewer=False, history_store=_null_store(tmp_path))
        assert pkg1.change_set_id == pkg2.change_set_id
        assert pkg1.drift_score == pkg2.drift_score
        assert pkg1.spec_confidence_score == pkg2.spec_confidence_score

    def test_schema_field_correct(self, tmp_path: Path) -> None:
        cs = ChangeSet(diff_text="", repo_path=tmp_path)
        pkg = verify(cs, use_reviewer=False, history_store=_null_store(tmp_path))
        assert pkg.schema_ == "evidence-package-v1"

    def test_functional_evidence_passed_through(self, tmp_path: Path) -> None:
        fe = FunctionalEvidence(tests_passed=True, tests_total=42, tests_failing=0)
        cs = ChangeSet(diff_text="", repo_path=tmp_path)
        pkg = verify(
            cs,
            use_reviewer=False,
            functional_evidence=fe,
            history_store=_null_store(tmp_path),
        )
        assert pkg.functional_evidence.tests_total == 42

    def test_reviewer_mock_integrates(self, tmp_path: Path) -> None:
        reviewer = MockReviewerAgent(available=True, confidence_delta=0.05)
        cs = ChangeSet(diff_text="--- a\n+++ b", repo_path=tmp_path)
        pkg = verify(
            cs,
            reviewer=reviewer,
            use_reviewer=True,
            history_store=_null_store(tmp_path),
        )
        assert pkg.independent_review is not None
        assert pkg.independent_review.available is True


# ---------------------------------------------------------------------------
# T030 / US3 — reviewer timeout fallback
# ---------------------------------------------------------------------------

class TestReviewerTimeout:
    def test_unavailable_reviewer_sets_flag(self, tmp_path: Path) -> None:
        reviewer = MockReviewerAgent(available=False)
        cs = ChangeSet(diff_text="--- a\n+++ b", repo_path=tmp_path)
        pkg = verify(
            cs,
            reviewer=reviewer,
            use_reviewer=True,
            history_store=_null_store(tmp_path),
        )
        assert EvidenceFlag.independent_review_unavailable in pkg.flags
        assert pkg.independent_review is not None
        assert pkg.independent_review.available is False

    def test_no_reviewer_skips_review(self, tmp_path: Path) -> None:
        cs = ChangeSet(diff_text="--- a\n+++ b", repo_path=tmp_path)
        pkg = verify(cs, use_reviewer=False, history_store=_null_store(tmp_path))
        assert pkg.independent_review is None


# ---------------------------------------------------------------------------
# T035 / US4 — rule promotion
# ---------------------------------------------------------------------------

class TestRulePromotion:
    def test_below_threshold_no_proposal(self) -> None:
        entries = [
            PatternHistoryEntry(type="layer_violation", pattern="src/foo.py", file="src/foo.py", ts="2026-01-01")
            for _ in range(4)
        ]
        proposals = compute_promotions(entries, [], threshold=5)
        assert proposals == []

    def test_at_threshold_creates_proposal(self) -> None:
        entries = [
            PatternHistoryEntry(type="layer_violation", pattern="src/foo.py", file="src/foo.py", ts="2026-01-01")
            for _ in range(5)
        ]
        proposals = compute_promotions(entries, [], threshold=5)
        assert len(proposals) == 1
        assert proposals[0].occurrence_count == 5

    def test_new_violations_count_toward_threshold(self) -> None:
        entries = [
            PatternHistoryEntry(type="layer_violation", pattern="src/foo.py", file="src/foo.py", ts="2026-01-01")
            for _ in range(3)
        ]
        violations = [
            ViolationFinding(
                violation_type=ViolationType.layer_violation,
                severity=Severity.medium,
                file="src/foo.py",
                message="x",
                remediation="y",
            )
            for _ in range(2)
        ]
        proposals = compute_promotions(entries, violations, threshold=5)
        assert len(proposals) == 1


# ---------------------------------------------------------------------------
# T039 — Multi-layer diff edge case
# ---------------------------------------------------------------------------

class TestMultiLayerDiff:
    """Multi-layer diff: violations from different layers all reported; highest severity drives verdict."""

    def test_multi_layer_all_violations_reported(self) -> None:
        """Violations from both signals/layer and commands/layer must both appear."""
        violations = [
            ViolationFinding(
                violation_type=ViolationType.layer_violation,
                severity=Severity.high,
                file="src/drift/signals/new_signal.py",
                rule_id="AVS",
                message="layer violation in signals",
                remediation="fix",
            ),
            ViolationFinding(
                violation_type=ViolationType.forbidden_dependency,
                severity=Severity.medium,
                file="src/drift/commands/new_cmd.py",
                rule_id="EDS",
                message="forbidden dep in commands",
                remediation="fix",
            ),
        ]
        score = compute_drift_score(violations)
        # high (0.75) + medium (0.5) = 1.25 → / 5.0 = 0.25
        assert score == pytest.approx(0.25)

    def test_highest_severity_drives_verdict(self) -> None:
        """When violations span layers, the highest severity must produce needs_fix."""
        violations = [
            ViolationFinding(
                violation_type=ViolationType.layer_violation,
                severity=Severity.critical,
                file="src/drift/signals/new_signal.py",
                rule_id="AVS",
                message="critical layer violation in signals",
                remediation="fix",
            ),
            ViolationFinding(
                violation_type=ViolationType.file_placement,
                severity=Severity.low,
                file="src/drift/commands/new_cmd.py",
                rule_id="PFS",
                message="placement warning in commands",
                remediation="fix",
            ),
        ]
        score = compute_drift_score(violations)
        rec = build_action_recommendation(score, 0.5, violations, set())
        # Critical violation must produce needs_fix regardless of low violations
        assert rec.verdict == Verdict.needs_fix
        assert rec.blocking_violation_count == 1

    def test_multi_layer_low_only_gives_needs_review_under_threshold(self) -> None:
        """All low-severity violations from multiple layers → no blocking, but violations present → needs_review."""
        violations = [
            ViolationFinding(
                violation_type=ViolationType.naming_convention,
                severity=Severity.low,
                file="src/drift/signals/foo.py",
                rule_id="MDS",
                message="naming issue in signals",
                remediation="fix",
            ),
            ViolationFinding(
                violation_type=ViolationType.naming_convention,
                severity=Severity.low,
                file="src/drift/commands/bar.py",
                rule_id="MDS",
                message="naming issue in commands",
                remediation="fix",
            ),
        ]
        score = compute_drift_score(violations)
        # 2 × low (0.25) = 0.5 → / 5.0 = 0.10 — score is low but violations present
        assert score == pytest.approx(0.10)
        rec = build_action_recommendation(score, 0.9, violations, set())
        # violations present (even low severity) → needs_review (not blocking, not automerge)
        assert rec.verdict == Verdict.needs_review
        assert rec.blocking_violation_count == 0

    def test_violation_count_correct_for_multi_layer(self) -> None:
        """All violations (one per changed layer) must be present in the returned list."""
        violations = [
            _violation_with(Severity.high, "src/drift/signals/a.py", ViolationType.layer_violation),
            _violation_with(Severity.medium, "src/drift/commands/b.py", ViolationType.forbidden_dependency),
            _violation_with(Severity.low, "src/drift/ingestion/c.py", ViolationType.file_placement),
        ]
        assert len(violations) == 3
        files = {v.file for v in violations}
        assert files == {
            "src/drift/signals/a.py",
            "src/drift/commands/b.py",
            "src/drift/ingestion/c.py",
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_package(
    drift_score: float = 0.0,
    spec_confidence: float = 1.0,
) -> EvidencePackage:
    return EvidencePackage(
        **{"schema": "evidence-package-v1"},
        version="0",
        change_set_id="empty",
        repo=".",
        verified_at=datetime.now(tz=UTC),
        drift_score=drift_score,
        spec_confidence_score=spec_confidence,
        action_recommendation=ActionRecommendation(
            verdict=Verdict.automerge,
            reason="test",
        ),
    )


def _violation(severity: Severity = Severity.medium) -> ViolationFinding:
    return ViolationFinding(
        violation_type=ViolationType.layer_violation,
        severity=severity,
        message="test violation",
        remediation="fix it",
    )


def _violation_with(
    severity: Severity,
    file: str,
    vtype: ViolationType = ViolationType.layer_violation,
) -> ViolationFinding:
    return ViolationFinding(
        violation_type=vtype,
        severity=severity,
        file=file,
        message=f"{vtype.value} in {file}",
        remediation="fix it",
    )


def _null_store(tmp_path: Path):  # type: ignore[return]
    from drift_verify._promoter import PatternHistoryStore
    return PatternHistoryStore(path=tmp_path / ".drift" / "pattern_history.jsonl")
