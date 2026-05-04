"""Ledger contract tests: override validation, version conflict, outcome updates (T007/T039)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from drift_cockpit._exceptions import (
    MissingOverrideJustificationError,
    VersionConflictError,
)
from drift_cockpit._ledger import (
    read_ledger,
    update_outcome,
    validate_override,
    write_ledger_entry,
)
from drift_cockpit._models import (
    DecisionStatus,
    LedgerEntry,
    OutcomeState,
)


def _entry(
    pr_id: str = "PR-1",
    recommended: DecisionStatus = DecisionStatus.go,
    human: DecisionStatus = DecisionStatus.go,
    override_reason: str | None = None,
    version: int = 1,
) -> LedgerEntry:
    return LedgerEntry(
        ledger_entry_id=f"le-{uuid.uuid4().hex[:8]}",
        pr_id=pr_id,
        recommended_status=recommended,
        human_status=human,
        override_reason=override_reason,
        decision_actor="test",
        version=version,
    )


class TestValidateOverride:
    def test_no_override_required_when_statuses_match(self):
        validate_override(_entry())  # should not raise

    def test_override_without_reason_raises(self):
        # Use model_construct to bypass Pydantic model_validator and test the
        # standalone validate_override function in isolation.
        from datetime import datetime

        from drift_cockpit._models import OutcomeSnapshot, OutcomeState
        entry = LedgerEntry.model_construct(
            ledger_entry_id="le-test",
            pr_id="PR-1",
            recommended_status=DecisionStatus.no_go,
            human_status=DecisionStatus.go,
            override_reason=None,
            decision_actor="test",
            evidence_refs=[],
            outcome_7d=OutcomeSnapshot(window="7d", state=OutcomeState.pending),
            outcome_30d=OutcomeSnapshot(window="30d", state=OutcomeState.pending),
            version=1,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        with pytest.raises(MissingOverrideJustificationError):
            validate_override(entry)

    def test_override_with_reason_is_valid(self):
        entry = _entry(
            recommended=DecisionStatus.no_go,
            human=DecisionStatus.go,
            override_reason="Approved by CTO — low risk confirmed.",
        )
        validate_override(entry)  # should not raise


class TestWriteReadLedger:
    def test_write_and_read(self, tmp_path: Path):
        entry = _entry(pr_id="PR-write")
        write_ledger_entry(entry, base=tmp_path)
        read = read_ledger("PR-write", base=tmp_path)
        assert len(read) == 1
        assert read[0].pr_id == "PR-write"

    def test_version_conflict_raises(self, tmp_path: Path):
        e1 = _entry(pr_id="PR-conflict", version=1)
        write_ledger_entry(e1, base=tmp_path)
        # Next entry must be version 2, not 1 again
        e2 = _entry(pr_id="PR-conflict", version=1)
        with pytest.raises(VersionConflictError):
            write_ledger_entry(e2, base=tmp_path)

    def test_sequential_versions(self, tmp_path: Path):
        e1 = _entry(pr_id="PR-seq", version=1)
        write_ledger_entry(e1, base=tmp_path)
        e2 = _entry(pr_id="PR-seq", version=2)
        write_ledger_entry(e2, base=tmp_path)
        entries = read_ledger("PR-seq", base=tmp_path)
        assert [e.version for e in entries] == [1, 2]


class TestUpdateOutcome:
    def test_update_7d_outcome(self, tmp_path: Path):
        e1 = _entry(pr_id="PR-outcome", version=1)
        write_ledger_entry(e1, base=tmp_path)
        updated = update_outcome(
            "PR-outcome",
            window="7d",
            state=OutcomeState.captured,
            rework_events=0,
            base=tmp_path,
        )
        assert updated.outcome_7d.state == OutcomeState.captured
        assert updated.version == 2

    def test_no_ledger_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match="No ledger entries"):
            update_outcome("PR-ghost", window="7d", state=OutcomeState.captured, base=tmp_path)
