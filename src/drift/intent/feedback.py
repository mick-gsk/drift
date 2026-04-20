"""Prioritised action-set generation for the building agent."""
from __future__ import annotations

from drift.intent._models import FeedbackActionItem, FeedbackResult, VerifyResult


def _estimate_complexity(missing_count: int) -> str:
    if missing_count <= 1:
        return "low"
    if missing_count <= 4:
        return "medium"
    return "high"


def generate_feedback(verify_result: VerifyResult) -> FeedbackResult:
    """Convert a VerifyResult into a prioritised FeedbackResult for the agent."""
    if verify_result.status == "fulfilled" or not verify_result.missing:
        return FeedbackResult(actions=[], estimated_complexity="low")

    actions = [
        FeedbackActionItem(
            priority=i + 1,
            action="add_feature",
            description=feature,
        )
        for i, feature in enumerate(verify_result.missing)
    ]
    return FeedbackResult(
        actions=actions,
        estimated_complexity=_estimate_complexity(len(actions)),
    )
