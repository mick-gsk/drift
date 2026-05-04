"""Contract tests for EvidencePackage invariants (TDD Red phase → Green)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from drift_verify._models import (
    ActionRecommendation,
    ChangeSet,
    EvidenceFlag,
    EvidencePackage,
    Verdict,
)
from drift_verify._verify import verify


def _pkg(**kwargs: object) -> EvidencePackage:
    defaults: dict[str, object] = {
        "schema": "evidence-package-v1",
        "version": "0",
        "change_set_id": "empty",
        "repo": ".",
        "verified_at": datetime.now(tz=UTC),
        "drift_score": 0.0,
        "spec_confidence_score": 1.0,
        "action_recommendation": ActionRecommendation(
            verdict=Verdict.automerge, reason="ok"
        ),
    }
    defaults.update(kwargs)
    return EvidencePackage(**defaults)


class TestEvidencePackageInvariants:
    def test_schema_always_evidence_package_v1(self) -> None:
        pkg = _pkg()
        assert pkg.schema_ == "evidence-package-v1"

    def test_scores_bounded(self) -> None:
        pkg = _pkg(drift_score=0.0, spec_confidence_score=1.0)
        assert 0.0 <= pkg.drift_score <= 1.0
        assert 0.0 <= pkg.spec_confidence_score <= 1.0

    def test_drift_score_above_one_rejected(self) -> None:
        with pytest.raises(Exception):
            _pkg(drift_score=1.1)

    def test_spec_confidence_below_zero_rejected(self) -> None:
        with pytest.raises(Exception):
            _pkg(spec_confidence_score=-0.1)

    def test_no_changes_flag_requires_zero_drift(self) -> None:
        with pytest.raises(Exception):
            _pkg(
                drift_score=0.5,
                flags=frozenset({EvidenceFlag.no_changes_detected}),
            )

    def test_no_changes_flag_requires_one_confidence(self) -> None:
        with pytest.raises(Exception):
            _pkg(
                spec_confidence_score=0.5,
                flags=frozenset({EvidenceFlag.no_changes_detected}),
            )

    def test_automerge_only_when_no_violations(self, tmp_path: Path) -> None:
        """Automerge is only returned when violations list is empty."""
        cs = ChangeSet(diff_text="", repo_path=tmp_path)
        from drift_verify._promoter import PatternHistoryStore
        pkg = verify(
            cs,
            use_reviewer=False,
            history_store=PatternHistoryStore(
                tmp_path / ".drift" / "pattern_history.jsonl"
            ),
        )
        if pkg.action_recommendation.verdict == Verdict.automerge:
            assert pkg.violations == []

    def test_package_has_required_fields(self, tmp_path: Path) -> None:
        cs = ChangeSet(diff_text="", repo_path=tmp_path)
        from drift_verify._promoter import PatternHistoryStore
        pkg = verify(
            cs,
            use_reviewer=False,
            history_store=PatternHistoryStore(
                tmp_path / ".drift" / "pattern_history.jsonl"
            ),
        )
        assert pkg.version is not None
        assert pkg.change_set_id is not None
        assert pkg.repo is not None
        assert pkg.verified_at is not None
        assert pkg.action_recommendation is not None
