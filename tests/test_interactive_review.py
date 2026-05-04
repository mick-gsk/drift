"""Tests for interactive feedback review (``drift analyze --review``)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from drift.models import Finding, FindingStatus, Severity, SignalType
from drift.output.interactive_review import (
    _CALIBRATION_HINT_THRESHOLD,
    review_findings,
)
from rich.console import Console

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_finding(
    signal: str = SignalType.PATTERN_FRAGMENTATION,
    file_path: str = "src/auth/handler.py",
    start_line: int = 42,
) -> Finding:
    f = Finding(
        signal_type=signal,
        severity=Severity.MEDIUM,
        score=0.65,
        title="Pattern fragmentation detected",
        description="Multiple divergent implementations",
        file_path=Path(file_path),
        start_line=start_line,
    )
    f.status = FindingStatus.ACTIVE
    return f


def _make_console() -> Console:
    """Return an in-memory console for output capture."""
    return Console(file=open("/dev/null", "w") if sys.platform != "win32" else open("nul", "w"))


def _record_exists(feedback_path: Path) -> bool:
    return feedback_path.exists() and bool(feedback_path.read_text(encoding="utf-8").strip())


def _load_verdicts(feedback_path: Path) -> list[str]:
    if not feedback_path.exists():
        return []
    verdicts = []
    for line in feedback_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            verdicts.append(json.loads(line)["verdict"])
    return verdicts


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReviewNoFindings:
    def test_returns_zero_for_empty_findings(self, tmp_path: Path) -> None:
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"
        console = Console(file=open(tmp_path / "out.txt", "w", encoding="utf-8"))  # noqa: SIM115
        with patch.object(sys.stdin, "isatty", return_value=True):
            result = review_findings([], feedback_path, console)
        assert result == 0
        assert not feedback_path.exists()

    def test_does_not_call_prompt_for_empty_findings(self, tmp_path: Path) -> None:
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"
        console = Console(file=open(tmp_path / "out.txt", "w", encoding="utf-8"))  # noqa: SIM115
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch("click.prompt") as mock_prompt,
        ):
            review_findings([], feedback_path, console)
        mock_prompt.assert_not_called()


class TestReviewNonTtyGuard:
    def test_returns_zero_when_not_tty(self, tmp_path: Path) -> None:
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"
        console = Console(file=open(tmp_path / "out.txt", "w", encoding="utf-8"))  # noqa: SIM115
        findings = [_make_finding()]
        with patch.object(sys.stdin, "isatty", return_value=False):
            result = review_findings(findings, feedback_path, console)
        assert result == 0
        assert not feedback_path.exists()

    def test_does_not_call_prompt_when_not_tty(self, tmp_path: Path) -> None:
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"
        console = Console(file=open(tmp_path / "out.txt", "w", encoding="utf-8"))  # noqa: SIM115
        findings = [_make_finding()]
        with (
            patch.object(sys.stdin, "isatty", return_value=False),
            patch("click.prompt") as mock_prompt,
        ):
            review_findings(findings, feedback_path, console)
        mock_prompt.assert_not_called()


class TestReviewVerdicts:
    def test_tp_saves_feedback_entry(self, tmp_path: Path) -> None:
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"
        console = Console(file=open(tmp_path / "out.txt", "w", encoding="utf-8"))  # noqa: SIM115
        findings = [_make_finding()]
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch("click.prompt", return_value="t"),
        ):
            result = review_findings(findings, feedback_path, console)
        assert result == 1
        assert _load_verdicts(feedback_path) == ["tp"]

    def test_fp_saves_feedback_entry(self, tmp_path: Path) -> None:
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"
        console = Console(file=open(tmp_path / "out.txt", "w", encoding="utf-8"))  # noqa: SIM115
        findings = [_make_finding()]
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch("click.prompt", return_value="f"),
        ):
            result = review_findings(findings, feedback_path, console)
        assert result == 1
        assert _load_verdicts(feedback_path) == ["fp"]

    def test_skip_saves_nothing(self, tmp_path: Path) -> None:
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"
        console = Console(file=open(tmp_path / "out.txt", "w", encoding="utf-8"))  # noqa: SIM115
        findings = [_make_finding()]
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch("click.prompt", return_value="s"),
        ):
            result = review_findings(findings, feedback_path, console)
        assert result == 0
        assert _load_verdicts(feedback_path) == []

    def test_tp_verdict_has_correct_signal_type(self, tmp_path: Path) -> None:
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"
        console = Console(file=open(tmp_path / "out.txt", "w", encoding="utf-8"))  # noqa: SIM115
        findings = [_make_finding(signal=SignalType.ARCHITECTURE_VIOLATION, start_line=10)]
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch("click.prompt", return_value="t"),
        ):
            review_findings(findings, feedback_path, console)
        raw = json.loads(feedback_path.read_text(encoding="utf-8").strip())
        assert raw["signal_type"] == SignalType.ARCHITECTURE_VIOLATION
        assert raw["start_line"] == 10
        assert raw["source"] == "user"

    def test_unknown_choice_skips_without_saving(self, tmp_path: Path) -> None:
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"
        console = Console(file=open(tmp_path / "out.txt", "w", encoding="utf-8"))  # noqa: SIM115
        findings = [_make_finding()]
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch("click.prompt", return_value="x"),
        ):
            result = review_findings(findings, feedback_path, console)
        assert result == 0
        assert _load_verdicts(feedback_path) == []


class TestReviewQuit:
    def test_quit_stops_early(self, tmp_path: Path) -> None:
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"
        console = Console(file=open(tmp_path / "out.txt", "w", encoding="utf-8"))  # noqa: SIM115
        # 3 findings, quit immediately
        findings = [_make_finding() for _ in range(3)]
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch("click.prompt", return_value="q"),
        ):
            result = review_findings(findings, feedback_path, console)
        assert result == 0
        assert _load_verdicts(feedback_path) == []

    def test_quit_after_one_verdict_saves_only_that_one(self, tmp_path: Path) -> None:
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"
        console = Console(file=open(tmp_path / "out.txt", "w", encoding="utf-8"))  # noqa: SIM115
        findings = [_make_finding() for _ in range(3)]
        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch("click.prompt", side_effect=["t", "q"]),
        ):
            result = review_findings(findings, feedback_path, console)
        assert result == 1
        assert _load_verdicts(feedback_path) == ["tp"]


class TestCalibrationHint:
    def _seed_feedback(self, feedback_path: Path, count: int) -> None:
        """Pre-populate feedback file with dummy entries."""
        from drift.calibration.feedback import FeedbackEvent, record_feedback

        for i in range(count):
            event = FeedbackEvent(
                signal_type=SignalType.PATTERN_FRAGMENTATION,
                file_path=f"src/file_{i}.py",
                verdict="tp",
                source="user",
                start_line=i + 1,
            )
            record_feedback(feedback_path, event)

    def test_calibration_hint_shown_at_threshold(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"
        # Seed 9 existing entries — one new "t" verdict will bring it to 10
        self._seed_feedback(feedback_path, _CALIBRATION_HINT_THRESHOLD - 1)

        out_file = tmp_path / "out.txt"
        console = Console(file=open(out_file, "w", encoding="utf-8"), highlight=False)  # noqa: SIM115
        findings = [_make_finding()]

        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch("click.prompt", return_value="t"),
        ):
            review_findings(findings, feedback_path, console)

        output = out_file.read_text(encoding="utf-8")
        assert "calibrat" in output.lower()

    def test_calibration_hint_not_shown_below_threshold(self, tmp_path: Path) -> None:
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"
        # Only 5 entries total (4 seed + 1 new)
        self._seed_feedback(feedback_path, 4)

        out_file = tmp_path / "out.txt"
        console = Console(file=open(out_file, "w", encoding="utf-8"), highlight=False)  # noqa: SIM115
        findings = [_make_finding()]

        with (
            patch.object(sys.stdin, "isatty", return_value=True),
            patch("click.prompt", return_value="t"),
        ):
            review_findings(findings, feedback_path, console)

        output = out_file.read_text(encoding="utf-8")
        # Should NOT show calibration hint
        assert "drift calibrate" not in output
