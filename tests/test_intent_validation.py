"""Tests for Phase C — Intent-Aware Validation.

Covers:
- Intent matcher: maps findings to violated requirements
- Requirement status model
- Intent status output rendering
- CLI --intent flag integration
"""

from __future__ import annotations

from pathlib import Path

from drift.intent.models import (
    IntentCategory,
    IntentContract,
    Requirement,
)

from drift.models import Finding, Severity

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finding(signal_type: str, title: str = "Test finding", file_path: str = "app.py") -> Finding:
    """Create a minimal Finding for testing."""
    return Finding(
        signal_type=signal_type,
        severity=Severity.MEDIUM,
        score=0.5,
        title=title,
        description=f"Description for {signal_type}",
        file_path=Path(file_path),
    )


def _contract(
    category: IntentCategory = IntentCategory.AUTH,
    requirements: list[Requirement] | None = None,
) -> IntentContract:
    """Create a minimal IntentContract for testing."""
    if requirements is None:
        requirements = [
            Requirement(
                id="req-1",
                description_plain="Nutzer können sich anmelden",
                description_technical="Auth flow with session management",
                priority="must",
                validation_signal="missing_authorization",
            ),
            Requirement(
                id="req-2",
                description_plain="Nur berechtigte Nutzer haben Zugriff",
                description_technical="Authorization checks on protected resources",
                priority="must",
                validation_signal="missing_authorization",
            ),
        ]
    return IntentContract(
        description="Eine App mit Login",
        category=category,
        requirements=requirements,
        language="de",
    )


# ---------------------------------------------------------------------------
# TestRequirementStatus
# ---------------------------------------------------------------------------


class TestRequirementStatus:
    """RequirementStatus model tests."""

    def test_fields(self) -> None:
        from drift.intent._matcher import RequirementStatus

        status = RequirementStatus(
            requirement_id="req-1",
            description_plain="Nutzer können sich anmelden",
            satisfied=True,
            violated_by=[],
        )
        assert status.requirement_id == "req-1"
        assert status.satisfied is True
        assert status.violated_by == []

    def test_violated_status(self) -> None:
        from drift.intent._matcher import RequirementStatus

        f = _finding("missing_authorization")
        status = RequirementStatus(
            requirement_id="req-1",
            description_plain="Auth check",
            satisfied=False,
            violated_by=[f],
        )
        assert status.satisfied is False
        assert len(status.violated_by) == 1


# ---------------------------------------------------------------------------
# TestIntentMatcher
# ---------------------------------------------------------------------------


class TestIntentMatcher:
    """Tests for match_findings_to_contracts()."""

    def test_match_finding_to_requirement(self) -> None:
        """Finding with signal_type matching validation_signal → violated."""
        from drift.intent._matcher import match_findings_to_contracts

        contract = _contract()
        findings = [_finding("missing_authorization")]

        statuses = match_findings_to_contracts(findings, [contract])

        # req-1 and req-2 both have validation_signal=missing_authorization
        violated = [s for s in statuses if not s.satisfied]
        assert len(violated) == 2
        for s in violated:
            assert len(s.violated_by) == 1
            assert s.violated_by[0].signal_type == "missing_authorization"

    def test_no_match_when_no_contracts(self) -> None:
        """Empty contract list → empty statuses."""
        from drift.intent._matcher import match_findings_to_contracts

        findings = [_finding("missing_authorization")]
        statuses = match_findings_to_contracts(findings, [])
        assert statuses == []

    def test_no_match_when_signal_differs(self) -> None:
        """Finding signal doesn't match any requirement → all satisfied."""
        from drift.intent._matcher import match_findings_to_contracts

        contract = _contract()
        findings = [_finding("broad_exception_monoculture")]

        statuses = match_findings_to_contracts(findings, [contract])

        assert all(s.satisfied for s in statuses)
        assert all(len(s.violated_by) == 0 for s in statuses)

    def test_requirement_without_signal_always_satisfied(self) -> None:
        """Requirements without validation_signal are always satisfied."""
        from drift.intent._matcher import match_findings_to_contracts

        req = Requirement(
            id="req-manual",
            description_plain="Muss schön aussehen",
            description_technical="UI aesthetics",
            priority="nice",
            validation_signal=None,
        )
        contract = _contract(requirements=[req])
        findings = [_finding("missing_authorization")]

        statuses = match_findings_to_contracts(findings, [contract])

        assert len(statuses) == 1
        assert statuses[0].satisfied is True

    def test_multiple_findings_same_signal(self) -> None:
        """Multiple findings matching same signal all collected."""
        from drift.intent._matcher import match_findings_to_contracts

        req = Requirement(
            id="req-1",
            description_plain="Auth",
            description_technical="Auth",
            priority="must",
            validation_signal="missing_authorization",
        )
        contract = _contract(requirements=[req])
        findings = [
            _finding("missing_authorization", file_path="auth.py"),
            _finding("missing_authorization", file_path="api.py"),
        ]

        statuses = match_findings_to_contracts(findings, [contract])

        assert len(statuses) == 1
        assert not statuses[0].satisfied
        assert len(statuses[0].violated_by) == 2

    def test_multiple_contracts(self) -> None:
        """Requirements from multiple contracts are all checked."""
        from drift.intent._matcher import match_findings_to_contracts

        req_auth = Requirement(
            id="req-auth",
            description_plain="Auth",
            description_technical="Auth",
            priority="must",
            validation_signal="missing_authorization",
        )
        req_error = Requirement(
            id="req-error",
            description_plain="Error handling",
            description_technical="Error handling",
            priority="must",
            validation_signal="broad_exception_monoculture",
        )
        c1 = _contract(requirements=[req_auth])
        c2 = _contract(
            category=IntentCategory.AUTOMATION,
            requirements=[req_error],
        )
        findings = [_finding("missing_authorization")]

        statuses = match_findings_to_contracts(findings, [c1, c2])

        assert len(statuses) == 2
        violated = [s for s in statuses if not s.satisfied]
        satisfied = [s for s in statuses if s.satisfied]
        assert len(violated) == 1
        assert violated[0].requirement_id == "req-auth"
        assert len(satisfied) == 1
        assert satisfied[0].requirement_id == "req-error"


# ---------------------------------------------------------------------------
# TestIntentStatusRendering
# ---------------------------------------------------------------------------


class TestIntentStatusRendering:
    """Tests for format_intent_status()."""

    def test_all_satisfied(self) -> None:
        """All requirements satisfied → all lines start with check."""
        from drift.intent._matcher import RequirementStatus
        from drift.intent._status import format_intent_status

        statuses = [
            RequirementStatus(
                requirement_id="req-1",
                description_plain="Daten werden gespeichert",
                satisfied=True,
                violated_by=[],
            ),
        ]
        lines = format_intent_status(statuses)
        assert any("✅" in line for line in lines)
        assert not any("❌" in line for line in lines)

    def test_violated_shows_cross(self) -> None:
        """Violated requirement → ❌ with finding info."""
        from drift.intent._matcher import RequirementStatus
        from drift.intent._status import format_intent_status

        f = _finding("missing_authorization")
        statuses = [
            RequirementStatus(
                requirement_id="req-1",
                description_plain="Nur berechtigte Nutzer haben Zugriff",
                satisfied=False,
                violated_by=[f],
            ),
        ]
        lines = format_intent_status(statuses)
        assert any("❌" in line for line in lines)
        assert any("Nur berechtigte Nutzer" in line for line in lines)

    def test_mixed_status(self) -> None:
        """Mix of satisfied and violated → both symbols present."""
        from drift.intent._matcher import RequirementStatus
        from drift.intent._status import format_intent_status

        f = _finding("missing_authorization")
        statuses = [
            RequirementStatus(
                requirement_id="req-1",
                description_plain="Daten werden gespeichert",
                satisfied=True,
                violated_by=[],
            ),
            RequirementStatus(
                requirement_id="req-2",
                description_plain="Auth ist vorhanden",
                satisfied=False,
                violated_by=[f],
            ),
        ]
        lines = format_intent_status(statuses)
        text = "\n".join(lines)
        assert "✅" in text
        assert "❌" in text

    def test_finding_count_shown(self) -> None:
        """Violated status shows how many findings triggered it."""
        from drift.intent._matcher import RequirementStatus
        from drift.intent._status import format_intent_status

        findings = [
            _finding("missing_authorization", file_path="a.py"),
            _finding("missing_authorization", file_path="b.py"),
        ]
        statuses = [
            RequirementStatus(
                requirement_id="req-1",
                description_plain="Auth check",
                satisfied=False,
                violated_by=findings,
            ),
        ]
        lines = format_intent_status(statuses)
        # Should mention the count of violations somewhere
        text = "\n".join(lines)
        assert "2" in text


# ---------------------------------------------------------------------------
# TestIntentSummary
# ---------------------------------------------------------------------------


class TestIntentSummary:
    """Tests for generate_intent_summary() — combines matching + rendering."""

    def test_summary_from_contract_and_findings(self) -> None:
        """End-to-end: contract + findings → human-readable summary lines."""
        from drift.intent._matcher import match_findings_to_contracts
        from drift.intent._status import format_intent_status

        contract = _contract()
        findings = [_finding("missing_authorization")]

        statuses = match_findings_to_contracts(findings, [contract])
        lines = format_intent_status(statuses)

        assert len(lines) >= 2  # at least one line per requirement
        text = "\n".join(lines)
        assert "❌" in text  # auth requirement violated

    def test_summary_clean_when_no_findings(self) -> None:
        """No findings → all requirements satisfied."""
        from drift.intent._matcher import match_findings_to_contracts
        from drift.intent._status import format_intent_status

        contract = _contract()
        statuses = match_findings_to_contracts([], [contract])
        lines = format_intent_status(statuses)

        text = "\n".join(lines)
        assert "✅" in text
        assert "❌" not in text
