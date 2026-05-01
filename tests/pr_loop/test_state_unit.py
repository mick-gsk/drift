"""Unit tests for loop state persistence (T023)."""

from __future__ import annotations

from pathlib import Path

import pytest

from drift.pr_loop._models import LoopExitStatus, LoopState
from drift.pr_loop._state import LoopStateError, load_loop_state, save_loop_state


class TestLoadLoopState:
    def test_returns_fresh_state_when_file_missing(self, tmp_path: Path) -> None:
        state = load_loop_state(pr_number=42, artifacts_dir=tmp_path)
        assert state.pr_number == 42
        assert state.round == 1
        assert state.status == LoopExitStatus.RUNNING
        assert state.addressed_comment_ids == []
        assert state.rounds == []

    def test_round_trip_preserves_all_fields(self, tmp_path: Path) -> None:
        original = LoopState(
            pr_number=99,
            round=3,
            status=LoopExitStatus.RUNNING,
            addressed_comment_ids=["c1", "c2"],
            rounds=[],
        )
        save_loop_state(original, tmp_path)
        loaded = load_loop_state(pr_number=99, artifacts_dir=tmp_path)
        assert loaded.pr_number == original.pr_number
        assert loaded.round == original.round
        assert loaded.status == original.status
        assert loaded.addressed_comment_ids == original.addressed_comment_ids

    def test_corrupted_json_raises_loop_state_error(self, tmp_path: Path) -> None:
        state_file = tmp_path / "pr-loop-42.json"
        state_file.write_text("NOT VALID JSON{{{{", encoding="utf-8")
        with pytest.raises(LoopStateError):
            load_loop_state(pr_number=42, artifacts_dir=tmp_path)

    def test_creates_artifacts_dir_on_save(self, tmp_path: Path) -> None:
        nested = tmp_path / "nested" / "artifacts"
        state = LoopState(pr_number=7, round=1, status=LoopExitStatus.RUNNING)
        save_loop_state(state, nested)
        assert (nested / "pr-loop-7.json").exists()

    def test_state_file_is_utf8(self, tmp_path: Path) -> None:
        state = LoopState(pr_number=1, round=1, status=LoopExitStatus.RUNNING)
        save_loop_state(state, tmp_path)
        raw = (tmp_path / "pr-loop-1.json").read_bytes()
        decoded = raw.decode("utf-8")  # should not raise
        assert "pr_number" in decoded
