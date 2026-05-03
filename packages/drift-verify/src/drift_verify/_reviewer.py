"""ReviewerAgentProtocol + MockReviewerAgent + DriftMcpReviewerAgent."""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from drift_verify._models import ChangeSet, IndependentReviewResult

_log = logging.getLogger(__name__)


@runtime_checkable
class ReviewerAgentProtocol(Protocol):
    """Protocol for independent reviewer agents (Constitution III / SC-006)."""

    def review(
        self,
        change_set: ChangeSet,
        *,
        timeout_seconds: float = 60.0,
    ) -> IndependentReviewResult:
        """Run independent review; return unavailable result on timeout/error."""
        ...


class MockReviewerAgent:
    """Test double — always returns a configurable result."""

    def __init__(
        self,
        *,
        available: bool = True,
        confidence_delta: float = 0.0,
        findings: list[str] | None = None,
        spec_criteria_violated: list[str] | None = None,
    ) -> None:
        self._result = IndependentReviewResult(
            available=available,
            confidence_delta=confidence_delta,
            findings=findings or [],
            spec_criteria_violated=spec_criteria_violated or [],
        )

    def review(
        self,
        change_set: ChangeSet,  # noqa: ARG002
        *,
        timeout_seconds: float = 60.0,  # noqa: ARG002
    ) -> IndependentReviewResult:
        return self._result


class DriftMcpReviewerAgent:
    """Production reviewer — delegates to drift.api.nudge (optional network call).

    This agent is outside the deterministic analysis pipeline. It is always
    opt-in (--no-reviewer disables it) and never called during signal computation.
    In CI environments without access, use --no-reviewer for network-free operation.
    """

    def review(
        self,
        change_set: ChangeSet,
        *,
        timeout_seconds: float = 60.0,
    ) -> IndependentReviewResult:
        try:
            from drift.api.nudge import nudge  # type: ignore[import-untyped]

            changed = [str(p) for p in change_set.changed_files]
            result = nudge(
                changed_files=changed,
                repo_path=str(change_set.repo_path),
                timeout_ms=int(timeout_seconds * 1000),
            )
            findings: list[str] = []
            delta = 0.0
            if result and hasattr(result, "direction"):
                if result.direction == "improving":
                    delta = 0.05
                elif result.direction == "degrading":
                    delta = -0.10
                    findings.append(f"Nudge direction: {result.direction}")
            return IndependentReviewResult(
                available=True,
                confidence_delta=delta,
                findings=findings,
            )
        except Exception as exc:  # noqa: BLE001
            _log.debug("DriftMcpReviewerAgent unavailable: %s", exc)
            return IndependentReviewResult(
                available=False,
                confidence_delta=0.0,
                findings=[],
            )
