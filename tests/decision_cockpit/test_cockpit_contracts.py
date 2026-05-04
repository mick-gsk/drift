"""Model invariant tests for DecisionBundle and LedgerEntry (T008)."""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from drift_cockpit._models import (
    DecisionBundle,
    DecisionStatus,
    LedgerEntry,
    OutcomeState,
)
from pydantic import ValidationError


class TestDecisionBundleInvariants:
    def test_no_evidence_forces_no_go(self):
        with pytest.raises(ValidationError, match="no_go"):
            DecisionBundle(
                pr_id="PR-1",
                status=DecisionStatus.go,  # invalid — no evidence
                confidence=0.9,
                evidence_sufficient=False,
                risk_score=0.1,
                version=1,
            )

    def test_valid_no_evidence_no_go(self):
        b = DecisionBundle(
            pr_id="PR-1",
            status=DecisionStatus.no_go,
            confidence=0.0,
            evidence_sufficient=False,
            risk_score=0.0,
            version=1,
        )
        assert b.status == DecisionStatus.no_go

    def test_confidence_bounded(self):
        with pytest.raises(ValidationError):
            DecisionBundle(
                pr_id="PR-1",
                status=DecisionStatus.go,
                confidence=1.5,  # out of range
                evidence_sufficient=True,
                risk_score=0.0,
                version=1,
            )

    def test_valid_bundle(self):
        b = DecisionBundle(
            pr_id="PR-1",
            status=DecisionStatus.go,
            confidence=0.90,
            evidence_sufficient=True,
            risk_score=0.1,
            version=1,
        )
        assert b.version == 1
        assert isinstance(b.computed_at, datetime)


class TestLedgerEntryInvariants:
    def test_override_without_reason_raises(self):
        with pytest.raises(ValidationError, match="override_reason"):
            LedgerEntry(
                ledger_entry_id=f"le-{uuid.uuid4().hex[:8]}",
                pr_id="PR-1",
                recommended_status=DecisionStatus.no_go,
                human_status=DecisionStatus.go,
                override_reason=None,  # missing — should fail
                decision_actor="actor",
                version=1,
            )

    def test_override_with_reason_valid(self):
        e = LedgerEntry(
            ledger_entry_id=f"le-{uuid.uuid4().hex[:8]}",
            pr_id="PR-1",
            recommended_status=DecisionStatus.no_go,
            human_status=DecisionStatus.go,
            override_reason="VP approved.",
            decision_actor="actor",
            version=1,
        )
        assert e.human_status == DecisionStatus.go

    def test_no_override_needed_when_same(self):
        e = LedgerEntry(
            ledger_entry_id=f"le-{uuid.uuid4().hex[:8]}",
            pr_id="PR-1",
            recommended_status=DecisionStatus.go,
            human_status=DecisionStatus.go,
            override_reason=None,
            decision_actor="actor",
            version=1,
        )
        assert e.version == 1

    def test_outcome_defaults_to_pending(self):
        e = LedgerEntry(
            ledger_entry_id=f"le-{uuid.uuid4().hex[:8]}",
            pr_id="PR-1",
            recommended_status=DecisionStatus.go,
            human_status=DecisionStatus.go,
            decision_actor="actor",
            version=1,
        )
        assert e.outcome_7d.state == OutcomeState.pending
        assert e.outcome_30d.state == OutcomeState.pending
