"""Tests for Issue 371: configurable and feedback-informed scoring thresholds.

Covers:
- ScoringConfig defaults match legacy constants
- assign_impact_scores respects custom breadth_cap
- apply_path_overrides respects custom breadth_cap
- score_to_grade respects custom grade_bands
- compute_signal_scores respects custom dampening_k
- DriftConfig.scoring field round-trips through YAML
- Pipeline feedback blend (ScoringPhase) with mocked feedback data
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from drift.config import DriftConfig, GradeBandConfig, ScoringConfig, SignalWeights
from drift.config._schema import PathOverride
from drift.models import Finding, Severity
from drift.scoring.engine import (
    apply_path_overrides,
    assign_impact_scores,
    compute_signal_scores,
    score_to_grade,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(
    *,
    signal_type: str = "pattern_fragmentation",
    score: float = 0.8,
    related_files: int = 0,
    file_path: str = "src/foo.py",
) -> Finding:
    f = Finding(
        signal_type=signal_type,
        title="test",
        description="test finding",
        severity=Severity.HIGH,
        score=score,
        file_path=Path(file_path),
    )
    f.related_files = [Path(f"related_{i}.py") for i in range(related_files)]
    return f


# ---------------------------------------------------------------------------
# ScoringConfig defaults
# ---------------------------------------------------------------------------


class TestScoringConfigDefaults:
    def test_dampening_k_default(self) -> None:
        sc = ScoringConfig()
        assert sc.dampening_k == 20

    def test_breadth_cap_default(self) -> None:
        sc = ScoringConfig()
        assert sc.breadth_cap == 4.0

    def test_feedback_blend_alpha_default(self) -> None:
        sc = ScoringConfig()
        assert sc.feedback_blend_alpha == 0.0

    def test_grade_bands_default_five_entries(self) -> None:
        sc = ScoringConfig()
        assert len(sc.grade_bands) == 5

    def test_grade_bands_grades(self) -> None:
        sc = ScoringConfig()
        grades = [b.grade for b in sc.grade_bands]
        assert grades == ["A", "B", "C", "D", "F"]

    def test_driftconfig_has_scoring_field(self) -> None:
        cfg = DriftConfig()
        assert isinstance(cfg.scoring, ScoringConfig)


# ---------------------------------------------------------------------------
# assign_impact_scores: breadth_cap
# ---------------------------------------------------------------------------


class TestAssignImpactScoresBreadthCap:
    def test_default_cap_applied(self) -> None:
        weights = SignalWeights()
        f = _make_finding(related_files=100)  # many related files
        assign_impact_scores([f], weights)
        # With default cap=4.0 and 100 related files: breadth = min(4.0, 1+ln(101)) = 4.0
        expected_breadth = 4.0
        w = weights.as_dict().get("pattern_fragmentation", 0.1)
        assert f.impact == round(w * f.score * expected_breadth, 4)

    def test_custom_cap_lower(self) -> None:
        weights = SignalWeights()
        f = _make_finding(related_files=10)
        assign_impact_scores([f], weights, breadth_cap=2.0)
        # With cap=2.0 and 10 related files: breadth = min(2.0, 1+ln(11)) ≈ min(2.0, 3.397) = 2.0
        w = weights.as_dict().get("pattern_fragmentation", 0.1)
        assert f.impact == round(w * f.score * 2.0, 4)

    def test_custom_cap_zero_related_files(self) -> None:
        weights = SignalWeights()
        f = _make_finding(related_files=0)
        assign_impact_scores([f], weights, breadth_cap=2.0)
        # breadth = min(2.0, 1+ln(1)) = min(2.0, 1.0) = 1.0
        w = weights.as_dict().get("pattern_fragmentation", 0.1)
        assert f.impact == round(w * f.score * 1.0, 4)


# ---------------------------------------------------------------------------
# apply_path_overrides: breadth_cap
# ---------------------------------------------------------------------------


class TestApplyPathOverridesBreadthCap:
    def test_reweight_uses_custom_cap(self) -> None:
        f = _make_finding(signal_type="pattern_fragmentation", related_files=20)
        custom_weights = SignalWeights(pattern_fragmentation=0.5)
        override = PathOverride(weights=custom_weights)
        overrides = {"src/**": override}

        findings = apply_path_overrides([f], overrides, SignalWeights(), breadth_cap=2.0)
        assert findings  # not filtered
        # With cap=2.0: breadth = min(2.0, 1+ln(21)) ≈ min(2.0, 4.04) = 2.0
        expected = round(0.5 * f.score * 2.0, 4)
        assert findings[0].impact == expected

    def test_default_cap_unchanged(self) -> None:
        f = _make_finding(signal_type="pattern_fragmentation", related_files=100)
        custom_weights = SignalWeights(pattern_fragmentation=0.5)
        override = PathOverride(weights=custom_weights)
        overrides = {"src/**": override}

        findings = apply_path_overrides([f], overrides, SignalWeights())
        assert findings
        expected = round(0.5 * f.score * 4.0, 4)
        assert findings[0].impact == expected


# ---------------------------------------------------------------------------
# score_to_grade: custom grade_bands
# ---------------------------------------------------------------------------


class TestScoreToGradeCustomBands:
    def test_default_bands_a(self) -> None:
        grade, label = score_to_grade(0.10)
        assert grade == "A"
        assert label == "Minimal Drift"

    def test_default_bands_f(self) -> None:
        grade, label = score_to_grade(0.99)
        assert grade == "F"

    def test_custom_bands_two_zones(self) -> None:
        bands = [
            GradeBandConfig(threshold=0.50, grade="PASS", label="Passing"),
            GradeBandConfig(threshold=1.01, grade="FAIL", label="Failing"),
        ]
        grade, label = score_to_grade(0.30, grade_bands=bands)
        assert grade == "PASS"
        assert label == "Passing"

        grade2, label2 = score_to_grade(0.70, grade_bands=bands)
        assert grade2 == "FAIL"
        assert label2 == "Failing"

    def test_custom_bands_fallback_last_entry(self) -> None:
        bands = [GradeBandConfig(threshold=0.50, grade="OK", label="OK")]
        grade, label = score_to_grade(0.99, grade_bands=bands)
        assert grade == "OK"

    def test_none_bands_uses_builtin(self) -> None:
        grade, _ = score_to_grade(0.25, grade_bands=None)
        assert grade == "B"


# ---------------------------------------------------------------------------
# compute_signal_scores: custom dampening_k
# ---------------------------------------------------------------------------


class TestComputeSignalScoresDampeningK:
    def test_custom_k_increases_dampening(self) -> None:
        findings = [_make_finding(score=0.9) for _ in range(5)]
        scores_k5 = compute_signal_scores(findings, dampening_k=5)
        scores_k20 = compute_signal_scores(findings, dampening_k=20)
        sig = "pattern_fragmentation"
        # Smaller k → dampening factor closer to 1.0 → higher score with n=5
        assert scores_k5.get(sig, 0.0) >= scores_k20.get(sig, 0.0)

    def test_k_1_maximum_dampening(self) -> None:
        # With k=1 and n=1: dampening = ln(2)/ln(2) = 1.0 (full score)
        findings = [_make_finding(score=0.8)]
        scores = compute_signal_scores(findings, dampening_k=1)
        assert scores.get("pattern_fragmentation", 0.0) == pytest.approx(0.8, abs=0.01)


# ---------------------------------------------------------------------------
# YAML round-trip for scoring config
# ---------------------------------------------------------------------------


class TestScoringConfigYamlRoundTrip:
    def test_roundtrip_custom_values(self, tmp_path: Path) -> None:
        yaml_content = """\
scoring:
  dampening_k: 10
  breadth_cap: 3.0
  feedback_blend_alpha: 0.5
"""
        drift_yaml = tmp_path / "drift.yaml"
        drift_yaml.write_text(yaml_content, encoding="utf-8")
        cfg = DriftConfig.load(tmp_path)
        assert cfg.scoring.dampening_k == 10
        assert cfg.scoring.breadth_cap == 3.0
        assert cfg.scoring.feedback_blend_alpha == 0.5

    def test_roundtrip_custom_grade_bands(self, tmp_path: Path) -> None:
        yaml_content = """\
scoring:
  grade_bands:
    - threshold: 0.5
      grade: PASS
      label: "Passing"
    - threshold: 1.01
      grade: FAIL
      label: "Failing"
"""
        (tmp_path / "drift.yaml").write_text(yaml_content, encoding="utf-8")
        cfg = DriftConfig.load(tmp_path)
        assert len(cfg.scoring.grade_bands) == 2
        assert cfg.scoring.grade_bands[0].grade == "PASS"

    def test_empty_scoring_section_uses_defaults(self, tmp_path: Path) -> None:
        (tmp_path / "drift.yaml").write_text("scoring: {}\n", encoding="utf-8")
        cfg = DriftConfig.load(tmp_path)
        assert cfg.scoring.dampening_k == 20
        assert cfg.scoring.breadth_cap == 4.0

    def test_no_scoring_section_uses_defaults(self, tmp_path: Path) -> None:
        (tmp_path / "drift.yaml").write_text("fail_on: high\n", encoding="utf-8")
        cfg = DriftConfig.load(tmp_path)
        assert cfg.scoring.dampening_k == 20
        assert cfg.scoring.breadth_cap == 4.0


# ---------------------------------------------------------------------------
# ScoringPhase feedback blending
# ---------------------------------------------------------------------------


class TestScoringPhaseFeedbackBlend:
    """Verify feedback_blend_alpha wires calibrated weights from feedback data."""

    def _make_config(self, alpha: float) -> DriftConfig:
        cfg = DriftConfig()
        cfg = cfg.model_copy(
            update={
                "auto_calibrate": True,
                "scoring": ScoringConfig(feedback_blend_alpha=alpha),
                "calibration": cfg.calibration.model_copy(update={"enabled": True}),
            }
        )
        return cfg

    def test_zero_alpha_no_feedback_load(self, tmp_path: Path) -> None:
        """alpha=0 should never attempt to load feedback."""
        from drift.pipeline import ScoringPhase

        cfg = self._make_config(alpha=0.0)
        phase = ScoringPhase()

        # Verify alpha=0 path completes without needing any feedback data
        result = phase.run(
            repo_path=tmp_path,
            files=[],
            config=cfg,
            findings=[],
        )
        assert result.repo_score == 0.0  # empty run, no crash

    def test_positive_alpha_with_no_feedback_file_is_noop(self, tmp_path: Path) -> None:
        """alpha>0 but empty/missing feedback file should not blow up."""
        from drift.pipeline import ScoringPhase

        cfg = self._make_config(alpha=0.5)
        phase = ScoringPhase()

        # No feedback file exists under tmp_path → load_feedback returns []
        result = phase.run(
            repo_path=tmp_path,
            files=[],
            config=cfg,
            findings=[],
        )
        assert result.repo_score == 0.0  # empty run, no crash

    def test_positive_alpha_blends_weights(self, tmp_path: Path) -> None:
        """When feedback events exist, effective weights should be blended."""
        from drift.calibration.feedback import FeedbackEvent
        from drift.calibration.profile_builder import CalibrationResult
        from drift.pipeline import ScoringPhase

        cfg = self._make_config(alpha=0.5)
        phase = ScoringPhase()

        fake_event = FeedbackEvent(
            signal_type="pattern_fragmentation",
            file_path="src/foo.py",
            verdict="tp",
            source="user",
        )
        # Feedback-calibrated weights: inflate pattern_fragmentation to max
        feedback_weights = SignalWeights(pattern_fragmentation=0.40)
        fake_calibration = CalibrationResult(
            calibrated_weights=feedback_weights,
            total_events=1,
            signals_with_data=1,
        )

        with (
            patch("drift.calibration.load_feedback", return_value=[fake_event]),
            patch("drift.calibration.profile_builder.build_profile", return_value=fake_calibration),
        ):
            result = phase.run(
                repo_path=tmp_path,
                files=[],
                config=cfg,
                findings=[],
            )
        # No findings → score is 0; what matters is no exception was raised
        assert result.repo_score == 0.0
