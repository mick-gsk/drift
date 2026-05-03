from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from click.testing import CliRunner
from drift.calibration.feedback import FeedbackEvent, load_feedback, record_feedback

from drift.commands.calibrate import calibrate
from drift.commands.feedback import feedback


def _cfg() -> SimpleNamespace:
    return SimpleNamespace(
        calibration=SimpleNamespace(
            enabled=True,
            auto_recalibrate=False,
            min_samples=1,
            fn_boost_factor=0.1,
            correlation_window_days=30,
            weak_fp_window_days=60,
            feedback_path=".drift-cache/feedback.jsonl",
            shared_feedback_path=".drift/team-feedback.jsonl",
            history_dir=".drift/history",
        ),
        weights=SimpleNamespace(as_dict=lambda: {}),
    )


def test_feedback_mark_writes_to_shared_feedback_path(tmp_path: Path) -> None:
    runner = CliRunner()
    cfg = _cfg()
    recorded: list[Path] = []

    def _record(path: Path, event: FeedbackEvent) -> None:
        recorded.append(path)

    with (
        patch("drift.config.DriftConfig.load", return_value=cfg),
        patch("drift.calibration.feedback.record_feedback", side_effect=_record),
    ):
        result = runner.invoke(
            feedback,
            [
                "mark",
                "--repo",
                str(tmp_path),
                "--mark",
                "tp",
                "--signal",
                "PFS",
                "--file",
                "src/a.py",
            ],
        )

    assert result.exit_code == 0
    assert recorded == [tmp_path / ".drift" / "team-feedback.jsonl"]


def test_feedback_push_to_shared_merges_local_events_without_duplicates(tmp_path: Path) -> None:
    runner = CliRunner()
    cfg = _cfg()

    local_path = tmp_path / ".drift-cache" / "feedback.jsonl"
    shared_path = tmp_path / ".drift" / "team-feedback.jsonl"

    duplicate = FeedbackEvent(
        signal_type="pattern_fragmentation",
        file_path="src/a.py",
        verdict="fp",
        source="user",
        timestamp="2026-04-13T00:00:00+00:00",
    )
    unique = FeedbackEvent(
        signal_type="architecture_violation",
        file_path="src/b.py",
        verdict="tp",
        source="user",
        timestamp="2026-04-13T00:00:01+00:00",
    )

    record_feedback(local_path, duplicate)
    record_feedback(local_path, unique)
    record_feedback(shared_path, duplicate)

    with patch("drift.config.DriftConfig.load", return_value=cfg):
        result = runner.invoke(
            feedback,
            ["push", "--repo", str(tmp_path), "--to-shared"],
        )

    assert result.exit_code == 0
    assert "Merged 1 new event(s)" in result.output

    merged = load_feedback(shared_path)
    assert len(merged) == 2


def test_calibrate_run_reads_from_shared_feedback_path(tmp_path: Path) -> None:
    runner = CliRunner()
    cfg = _cfg()
    seen_paths: list[Path] = []

    def _load(path: Path) -> list[FeedbackEvent]:
        seen_paths.append(path)
        return []

    with (
        patch("drift.config.DriftConfig.load", return_value=cfg),
        patch("drift.calibration.feedback.load_feedback", side_effect=_load),
    ):
        result = runner.invoke(calibrate, ["run", "--repo", str(tmp_path)])

    assert result.exit_code == 0
    assert seen_paths == [tmp_path / ".drift" / "team-feedback.jsonl"]
