"""Tests for recommendation_refiner — context-aware recommendation enrichment."""

from __future__ import annotations

from pathlib import Path

from drift.models import Finding, Severity
from drift.recommendation_refiner import refine
from drift.recommendations import Recommendation
from drift.reward_chain import RewardScore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_finding(
    *,
    file_path: str = "src/handler.py",
    symbol: str | None = "handle_request",
    start_line: int = 42,
    finding_context: str | None = None,
) -> Finding:
    return Finding(
        signal_type="pattern_fragmentation",
        severity=Severity.MEDIUM,
        score=0.7,
        title="Pattern fragmentation",
        description="Fragmented pattern detected.",
        file_path=Path(file_path),
        start_line=start_line,
        symbol=symbol,
        finding_context=finding_context,
    )


def _make_rec(description: str = "Consider reviewing the fragmented code.") -> Recommendation:
    return Recommendation(
        title="Consolidate patterns",
        description=description,
        effort="medium",
        impact="medium",
        file_path=Path("src/handler.py"),
        related_findings=["pfs-001"],
    )


def _make_reward(
    total: float = 0.3,
    fix_speed: float = 0.2,
    specificity: float = 0.2,
    **kwargs: float,
) -> RewardScore:
    return RewardScore(
        total=total,
        breakdown={
            "fix_speed": fix_speed,
            "specificity": specificity,
            "effort_accuracy": kwargs.get("effort_accuracy", 0.8),
            "no_regression": kwargs.get("no_regression", 1.0),
        },
        confidence=0.8,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRefine:
    def test_good_enough_returns_unchanged(self) -> None:
        """Recommendations with total >= 0.7 skip refinement."""
        rec = _make_rec("This is already good.")
        reward = _make_reward(total=0.8, fix_speed=0.9, specificity=0.9)
        refined = refine(rec, _make_finding(), reward)
        assert refined.description == rec.description

    def test_does_not_mutate_original(self) -> None:
        """Original recommendation must not be mutated (F-15)."""
        rec = _make_rec()
        original_desc = rec.description
        reward = _make_reward(fix_speed=0.1, specificity=0.1)
        refine(rec, _make_finding(), reward)
        assert rec.description == original_desc

    def test_enriches_location_on_low_fix_speed(self) -> None:
        rec = _make_rec("Fix the fragmented code.")
        reward = _make_reward(fix_speed=0.1)
        refined = refine(rec, _make_finding(), reward)
        assert "src/handler.py" in refined.description
        assert "handle_request" in refined.description

    def test_replaces_generic_verbs_on_low_specificity(self) -> None:
        rec = _make_rec("Consider reviewing the fragmented code.")
        reward = _make_reward(specificity=0.1, fix_speed=0.5)  # fix_speed OK
        refined = refine(rec, _make_finding(), reward)
        # "Consider" → "Extract" and "reviewing" → "inspecting"
        assert (
            "Consider" not in refined.description
            or "consider" not in refined.description.lower()
        )

    def test_context_suffix_test(self) -> None:
        finding = _make_finding(finding_context="test")
        rec = _make_rec("Fix the code.")
        reward = _make_reward()
        refined = refine(rec, finding, reward)
        assert "test code" in refined.description

    def test_context_suffix_generated(self) -> None:
        finding = _make_finding(finding_context="generated")
        rec = _make_rec("Fix the code.")
        reward = _make_reward()
        refined = refine(rec, finding, reward)
        assert "generated code" in refined.description

    def test_no_double_suffix(self) -> None:
        """Context suffix is only appended once."""
        finding = _make_finding(finding_context="test")
        rec = _make_rec("Fix the code.")
        reward = _make_reward()
        refined1 = refine(rec, finding, reward)
        refined2 = refine(refined1, finding, reward)
        assert refined2.description.count("test code") == 1

    def test_max_iterations_respected(self) -> None:
        """At most max_iterations refinement passes."""
        rec = _make_rec("Consider reviewing the fragmented code.")
        reward = _make_reward(fix_speed=0.1, specificity=0.1)
        refined = refine(rec, _make_finding(), reward, max_iterations=1)
        # With only 1 iteration, only fix_speed is addressed (location enrichment)
        assert "src/handler.py" in refined.description
        # Generic verbs may NOT have been replaced since second iteration was skipped
        # (but context suffix is applied regardless)

    def test_production_context_no_suffix(self) -> None:
        finding = _make_finding(finding_context=None)
        rec = _make_rec("Fix the code.")
        reward = _make_reward()
        refined = refine(rec, finding, reward)
        assert "test code" not in refined.description
        assert "generated code" not in refined.description
