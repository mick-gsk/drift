"""Tests for recommendation_calibrator — effort calibration from outcomes."""

from __future__ import annotations

from pathlib import Path

from drift.calibration.recommendation_calibrator import (
    EffortCalibration,
    calibrate_efforts,
    load_calibration,
    load_effort,
    save_calibration,
)

from drift.outcome_tracker import Outcome

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_outcomes(
    signal_type: str,
    days_values: list[float],
    *,
    suppressed: bool = False,
) -> list[Outcome]:
    """Create resolved, non-suppressed outcomes for testing."""
    return [
        Outcome(
            fingerprint=f"{signal_type}_{i}",
            signal_type=signal_type,
            recommendation_title="Fix",
            reported_at="2024-01-01T00:00:00+00:00",
            resolved_at="2024-01-10T00:00:00+00:00",
            days_to_fix=d,
            effort_estimate="medium",
            was_suppressed=suppressed,
        )
        for i, d in enumerate(days_values)
    ]


# ---------------------------------------------------------------------------
# calibrate_efforts
# ---------------------------------------------------------------------------

class TestCalibrateEfforts:
    def test_basic_low_effort(self) -> None:
        outcomes = _make_outcomes("pfs", [0.5] * 15)
        cals = calibrate_efforts(outcomes)
        assert len(cals) == 1
        assert cals[0].effort == "low"
        assert cals[0].sample_size == 15

    def test_basic_medium_effort(self) -> None:
        outcomes = _make_outcomes("avs", [3.0] * 12)
        cals = calibrate_efforts(outcomes)
        assert cals[0].effort == "medium"

    def test_basic_high_effort(self) -> None:
        outcomes = _make_outcomes("dca", [10.0] * 10)
        cals = calibrate_efforts(outcomes)
        assert cals[0].effort == "high"

    def test_min_samples_enforced(self) -> None:
        """Signal types with < min_samples are excluded (F-18)."""
        outcomes = _make_outcomes("pfs", [1.0] * 5)  # below default 10
        cals = calibrate_efforts(outcomes)
        assert len(cals) == 0

    def test_custom_min_samples(self) -> None:
        outcomes = _make_outcomes("pfs", [1.0] * 5)
        cals = calibrate_efforts(outcomes, min_samples=5)
        assert len(cals) == 1

    def test_suppressed_excluded(self) -> None:
        outcomes = _make_outcomes("pfs", [1.0] * 15, suppressed=True)
        cals = calibrate_efforts(outcomes)
        assert len(cals) == 0

    def test_unresolved_excluded(self) -> None:
        outcomes = [
            Outcome(
                fingerprint=f"pfs_{i}",
                signal_type="pfs",
                recommendation_title="Fix",
                reported_at="2024-01-01T00:00:00+00:00",
                resolved_at=None,
                days_to_fix=None,
                effort_estimate="medium",
            )
            for i in range(20)
        ]
        cals = calibrate_efforts(outcomes)
        assert len(cals) == 0

    def test_multiple_signal_types(self) -> None:
        outcomes = (
            _make_outcomes("pfs", [0.5] * 10)
            + _make_outcomes("avs", [3.0] * 10)
        )
        cals = calibrate_efforts(outcomes)
        assert len(cals) == 2
        efforts = {c.signal_type: c.effort for c in cals}
        assert efforts["pfs"] == "low"
        assert efforts["avs"] == "medium"


# ---------------------------------------------------------------------------
# save/load roundtrip
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_save_load_roundtrip(self, tmp_path: Path) -> None:
        calibrations = [
            EffortCalibration(
                signal_type="pfs",
                effort="low",
                sample_size=15,
                median_days_to_fix=0.5,
                calibrated_at="2024-01-01T00:00:00+00:00",
            ),
        ]
        cal_path = tmp_path / "calibration.json"
        save_calibration(calibrations, cal_path)
        loaded = load_calibration(cal_path)
        assert loaded == {"pfs": "low"}

    def test_load_missing_file(self, tmp_path: Path) -> None:
        cal_path = tmp_path / "missing.json"
        assert load_calibration(cal_path) == {}

    def test_load_corrupt_file(self, tmp_path: Path) -> None:
        cal_path = tmp_path / "corrupt.json"
        cal_path.write_text("not json", encoding="utf-8")
        assert load_calibration(cal_path) == {}

    def test_load_effort_convenience(self, tmp_path: Path) -> None:
        calibrations = [
            EffortCalibration(
                signal_type="pfs",
                effort="low",
                sample_size=15,
                median_days_to_fix=0.5,
                calibrated_at="2024-01-01T00:00:00+00:00",
            ),
        ]
        cal_path = tmp_path / "calibration.json"
        save_calibration(calibrations, cal_path)
        assert load_effort("pfs", cal_path) == "low"
        assert load_effort("unknown", cal_path) is None
        assert load_effort("pfs", None) is None
