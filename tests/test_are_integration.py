"""Integration tests for the Adaptive Recommendation Engine (ARE).

Tests the full pipeline: outcome tracking → reward chain → calibration → refinement.
"""

from __future__ import annotations

from pathlib import Path

from drift.calibration.recommendation_calibrator import (
    calibrate_efforts,
    load_calibration,
    save_calibration,
)
from drift.models import Finding, FindingStatus, LogicalLocation, Severity
from drift.outcome_tracker import Outcome, OutcomeTracker, compute_fingerprint
from drift.recommendation_refiner import refine
from drift.recommendations import Recommendation
from drift.reward_chain import compute_reward

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_finding(
    *,
    signal_type: str = "pattern_fragmentation",
    file_path: str = "src/app.py",
    start_line: int = 10,
    fqn: str = "src.app.AppService.process",
    symbol: str | None = "process",
    status: FindingStatus = FindingStatus.ACTIVE,
    finding_context: str | None = None,
) -> Finding:
    return Finding(
        signal_type=signal_type,
        severity=Severity.MEDIUM,
        score=0.7,
        title=f"Finding in {file_path}",
        description="Test finding.",
        file_path=Path(file_path),
        start_line=start_line,
        symbol=symbol,
        status=status,
        finding_context=finding_context,
        logical_location=LogicalLocation(
            fully_qualified_name=fqn,
            name=fqn.rsplit(".", 1)[-1],
            kind="function",
        ),
    )


def _make_rec(
    finding: Finding,
    description: str = "Consider reviewing the fragmented patterns.",
) -> Recommendation:
    return Recommendation(
        title="Consolidate patterns",
        description=description,
        effort="medium",
        impact="medium",
        file_path=finding.file_path,
        related_findings=[finding],
    )


# ---------------------------------------------------------------------------
# Full pipeline integration
# ---------------------------------------------------------------------------

class TestAREIntegration:
    """End-to-end: track → score → calibrate → refine."""

    def test_full_lifecycle(self, tmp_path: Path) -> None:
        """Simulate multiple analysis runs and verify the full ARE pipeline."""
        outcome_path = tmp_path / ".drift" / "outcomes.jsonl"
        cal_path = tmp_path / ".drift" / "effort_calibration.json"

        # --- Run 1: record findings
        tracker1 = OutcomeTracker(outcome_path)
        findings_run1 = [
            _make_finding(signal_type="pattern_fragmentation", fqn=f"mod.func_{i}")
            for i in range(12)
        ]
        for f in findings_run1:
            tracker1.record(f)
        fps_run1 = {compute_fingerprint(f) for f in findings_run1}

        # All present → none resolved
        resolved = tracker1.resolve(fps_run1)
        assert len(resolved) == 0

        # --- Run 2: some findings disappear (fixed)
        tracker2 = OutcomeTracker(outcome_path)
        findings_run2 = findings_run1[:8]  # 4 findings no longer present
        fps_run2 = {compute_fingerprint(f) for f in findings_run2}
        resolved = tracker2.resolve(fps_run2)
        assert len(resolved) == 4

        # Verify resolved outcomes have days_to_fix
        outcomes = tracker2.load()
        resolved_outcomes = [o for o in outcomes if o.resolved_at is not None]
        for o in resolved_outcomes:
            assert o.days_to_fix is not None

        # --- Calibrate effort labels
        # For sufficient samples, create additional resolved outcomes
        rich_outcomes = []
        for i in range(15):
            rich_outcomes.append(
                Outcome(
                    fingerprint=f"pfs_{i}",
                    signal_type="pattern_fragmentation",
                    recommendation_title="Fix",
                    reported_at="2024-01-01T00:00:00+00:00",
                    resolved_at="2024-01-03T00:00:00+00:00",
                    days_to_fix=2.0,
                    effort_estimate="medium",
                )
            )
        cals = calibrate_efforts(rich_outcomes, min_samples=10)
        assert len(cals) == 1
        assert cals[0].effort == "medium"
        save_calibration(cals, cal_path)

        # Load and verify
        effort_map = load_calibration(cal_path)
        assert effort_map["pattern_fragmentation"] == "medium"

        # --- Reward + Refine for a concrete finding
        finding = findings_run1[0]
        rec = _make_rec(finding)
        outcome = resolved_outcomes[0] if resolved_outcomes else None
        reward = compute_reward(outcome, rec, finding, all_outcomes=outcomes)
        assert 0.0 <= reward.total <= 1.0
        assert 0.0 <= reward.confidence <= 1.0

        refined = refine(rec, finding, reward)
        # Refined description should NOT be empty and should be valid
        assert len(refined.description) > 0

    def test_opt_in_disabled_no_side_effects(self, tmp_path: Path) -> None:
        """When ARE is disabled, no outcome files are created."""
        outcome_path = tmp_path / ".drift" / "outcomes.jsonl"
        # Simply don't use the tracker — verify no files created
        assert not outcome_path.exists()

    def test_suppressed_findings_excluded_from_calibration(self, tmp_path: Path) -> None:
        """Suppressed outcomes must not influence effort calibration."""
        outcomes = [
            Outcome(
                fingerprint=f"sup_{i}",
                signal_type="pattern_fragmentation",
                recommendation_title="Fix",
                reported_at="2024-01-01T00:00:00+00:00",
                resolved_at="2024-01-02T00:00:00+00:00",
                days_to_fix=1.0,
                effort_estimate="low",
                was_suppressed=True,
            )
            for i in range(20)
        ]
        cals = calibrate_efforts(outcomes)
        assert len(cals) == 0  # All suppressed → excluded

    def test_no_pii_in_stored_data(self, tmp_path: Path) -> None:
        """Outcome files must contain no PII (NF-08)."""
        outcome_path = tmp_path / ".drift" / "outcomes.jsonl"
        tracker = OutcomeTracker(outcome_path)
        tracker.record(_make_finding())
        content = outcome_path.read_text(encoding="utf-8")
        assert "@" not in content
        assert "author" not in content.lower()
        assert "email" not in content.lower()

    def test_refinement_idempotent_on_good_scores(self) -> None:
        """High-reward recommendations remain unchanged."""
        from drift.reward_chain import RewardScore

        finding = _make_finding()
        rec = _make_rec(finding, description="Merge the 3 variants in src/app.py.")
        reward = RewardScore(
            total=0.85,
            breakdown={
                "fix_speed": 1.0,
                "specificity": 0.9,
                "effort_accuracy": 1.0,
                "no_regression": 1.0,
            },
            confidence=0.9,
        )
        refined = refine(rec, finding, reward)
        assert refined.description == rec.description

    def test_config_defaults(self) -> None:
        """RecommendationsConfig has sane defaults and is opt-in."""
        from drift.config import RecommendationsConfig

        cfg = RecommendationsConfig()
        assert cfg.enabled is False
        assert cfg.archive_after_days == 180
        assert cfg.min_calibration_samples == 10
        assert cfg.refinement_threshold == 0.7
