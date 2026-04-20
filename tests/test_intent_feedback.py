from __future__ import annotations

from drift.intent._models import FeedbackResult, VerifyResult
from drift.intent.feedback import _estimate_complexity, generate_feedback


def _make_verify_incomplete(missing: list[str]) -> VerifyResult:
    return VerifyResult(
        status="incomplete",
        confidence=0.4,
        missing=missing,
        agent_feedback="Bitte implementiere: " + ", ".join(missing),
        iteration=2,
    )


def test_generate_feedback_returns_one_action_per_missing():
    result = _make_verify_incomplete(["Finanzverwaltung", "Export-Funktion"])
    feedback = generate_feedback(result)
    assert isinstance(feedback, FeedbackResult)
    assert len(feedback.actions) == 2


def test_generate_feedback_priorities_ordered():
    result = _make_verify_incomplete(["A", "B", "C"])
    feedback = generate_feedback(result)
    priorities = [a.priority for a in feedback.actions]
    assert priorities == sorted(priorities)


def test_generate_feedback_all_add_feature():
    result = _make_verify_incomplete(["Finanzverwaltung"])
    feedback = generate_feedback(result)
    assert all(a.action == "add_feature" for a in feedback.actions)


def test_generate_feedback_fulfilled_returns_empty():
    result = VerifyResult(
        status="fulfilled",
        confidence=0.95,
        missing=[],
        agent_feedback="",
        iteration=1,
    )
    feedback = generate_feedback(result)
    assert feedback.actions == []
    assert feedback.estimated_complexity == "low"


def test_estimate_complexity_low():
    assert _estimate_complexity(1) == "low"


def test_estimate_complexity_medium():
    assert _estimate_complexity(3) == "medium"


def test_estimate_complexity_high():
    assert _estimate_complexity(6) == "high"
