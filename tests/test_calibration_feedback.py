"""RED tests for FR-011b: FIFO cap on feedback.jsonl.

These tests define the contract for record_feedback() max_feedback_events
parameter. They MUST FAIL before T006 implementation and pass after.
"""

from __future__ import annotations

import json
from pathlib import Path

from drift.calibration.feedback import FeedbackEvent, record_feedback


def _make_event(signal: str, verdict: str = "fp") -> FeedbackEvent:
    return FeedbackEvent(
        signal_type=signal,
        file_path="src/foo.py",
        verdict=verdict,  # type: ignore[arg-type]
        source="user",
    )


class TestRecordFeedbackFifoCap:
    """FR-011b: FIFO cap — newest N events retained, oldest discarded."""

    def test_cap_retains_only_newest_events(self, tmp_path: Path) -> None:
        """With max_feedback_events=3 and 5 appended events, only 3 remain."""
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"

        for i in range(5):
            event = _make_event(f"signal_{i}")
            record_feedback(feedback_path, event, max_feedback_events=3)

        lines = feedback_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 3, f"Expected 3 lines (FIFO cap=3), got {len(lines)}"

    def test_cap_keeps_newest_events(self, tmp_path: Path) -> None:
        """The 3 retained events must be the LAST 3 appended (newest)."""
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"

        for i in range(5):
            event = _make_event(f"signal_{i}")
            record_feedback(feedback_path, event, max_feedback_events=3)

        lines = feedback_path.read_text(encoding="utf-8").splitlines()
        retained_signals = [json.loads(line)["signal_type"] for line in lines]
        assert retained_signals == ["signal_2", "signal_3", "signal_4"], (
            f"Expected newest 3 signals, got {retained_signals}"
        )

    def test_cap_zero_means_unlimited(self, tmp_path: Path) -> None:
        """Default cap=0 (unlimited) — all 5 events must be retained."""
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"

        for i in range(5):
            event = _make_event(f"signal_{i}")
            record_feedback(feedback_path, event, max_feedback_events=0)

        lines = feedback_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 5, f"Expected 5 lines with no cap, got {len(lines)}"

    def test_cap_below_existing_count_truncates_on_first_call(self, tmp_path: Path) -> None:
        """If file already has N events and cap=2, next append → cap enforced."""
        feedback_path = tmp_path / ".drift" / "feedback.jsonl"

        # Pre-populate with 4 events without cap
        for i in range(4):
            record_feedback(feedback_path, _make_event(f"pre_{i}"))

        # One more with cap=2
        record_feedback(feedback_path, _make_event("last"), max_feedback_events=2)

        lines = feedback_path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2, f"Expected 2 lines after cap=2, got {len(lines)}"
        last_signal = json.loads(lines[-1])["signal_type"]
        assert last_signal == "last", f"Last line must be 'last', got {last_signal}"
