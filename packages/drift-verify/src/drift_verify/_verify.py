"""Public verify() API — orchestrates checker, reviewer, promoter."""

from __future__ import annotations

import importlib.metadata
import logging
from datetime import UTC, datetime

from drift_verify._checker import (
    build_action_recommendation,
    compute_drift_score,
    compute_spec_confidence,
    run_deterministic_checks,
)
from drift_verify._models import (
    ChangeSet,
    EvidenceFlag,
    EvidencePackage,
    FunctionalEvidence,
    IndependentReviewResult,
    compute_change_set_id,
)
from drift_verify._promoter import (
    PatternHistoryStore,
    compute_promotions,
    record_violations,
)
from drift_verify._reviewer import (
    DriftMcpReviewerAgent,
    MockReviewerAgent,
    ReviewerAgentProtocol,
)

_log = logging.getLogger(__name__)

_UNAVAILABLE_REVIEWER = MockReviewerAgent(available=False)


def verify(
    change_set: ChangeSet,
    *,
    reviewer: ReviewerAgentProtocol | None = None,
    use_reviewer: bool = True,
    reviewer_timeout: float = 60.0,
    functional_evidence: FunctionalEvidence | None = None,
    threshold_drift: float = 0.2,
    threshold_confidence: float = 0.8,
    promote_threshold: int = 5,
    history_store: PatternHistoryStore | None = None,
) -> EvidencePackage:
    """Run evidence-based drift verification on a ChangeSet.

    Args:
        change_set: The diff/changed files to verify (caller-provided).
        reviewer: Optional ReviewerAgentProtocol implementation. Defaults to
            DriftMcpReviewerAgent when use_reviewer=True.
        use_reviewer: When False, skips independent review entirely (--no-reviewer).
        reviewer_timeout: Timeout in seconds for the reviewer agent.
        functional_evidence: Caller-provided CI evidence (FR-006). drift verify
            does NOT invoke pytest/ruff internally.
        threshold_drift: Max drift_score for automerge verdict.
        threshold_confidence: Min spec_confidence for automerge verdict.
        promote_threshold: Occurrences needed before a rule promotion is proposed.
        history_store: Overridable PatternHistoryStore (for testing).
    """
    # --- Deterministic check ---
    violations, flags = run_deterministic_checks(change_set)

    # --- Scores ---
    drift_score = (
        0.0
        if EvidenceFlag.no_changes_detected in flags
        else compute_drift_score(violations)
    )
    spec_confidence = (
        1.0
        if EvidenceFlag.no_changes_detected in flags
        else compute_spec_confidence(change_set, violations)
    )

    # --- Independent review (optional, synchronous) ---
    independent_review: IndependentReviewResult | None = None
    if use_reviewer and EvidenceFlag.no_changes_detected not in flags:
        active_reviewer: ReviewerAgentProtocol = reviewer or DriftMcpReviewerAgent()
        independent_review = active_reviewer.review(
            change_set, timeout_seconds=reviewer_timeout
        )
        if not independent_review.available:
            flags.add(EvidenceFlag.independent_review_unavailable)
        else:
            spec_confidence = min(
                1.0,
                max(0.0, spec_confidence + independent_review.confidence_delta),
            )

    # --- Action recommendation ---
    action = build_action_recommendation(
        drift_score,
        spec_confidence,
        violations,
        flags,
        threshold_drift=threshold_drift,
        threshold_confidence=threshold_confidence,
        independent_review=independent_review,
    )

    # --- Rule promotion ---
    store = history_store or PatternHistoryStore(
        path=change_set.repo_path / ".drift" / "pattern_history.jsonl"
    )
    history = store.load()
    promotions = compute_promotions(history, violations, promote_threshold)
    if violations:
        record_violations(violations, store)

    # --- Version ---
    try:
        version = importlib.metadata.version("drift-analyzer")
    except importlib.metadata.PackageNotFoundError:
        version = "0.0.0"

    return EvidencePackage(
        **{"schema": "evidence-package-v1"},
        version=version,
        change_set_id=compute_change_set_id(change_set.diff_text),
        repo=change_set.repo_path.as_posix(),
        verified_at=datetime.now(tz=UTC),
        drift_score=drift_score,
        spec_confidence_score=spec_confidence,
        action_recommendation=action,
        violations=violations,
        functional_evidence=functional_evidence or FunctionalEvidence(),
        independent_review=independent_review,
        rule_promotions=promotions,
        flags=frozenset(flags),
    )
