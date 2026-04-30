"""State persistence for the PR review loop (T011)."""

from __future__ import annotations

import json
from pathlib import Path

from drift.pr_loop._models import LoopExitStatus, LoopState


class LoopStateError(Exception):
    """Raised when loop state file is missing or corrupted."""


def load_loop_state(pr_number: int, artifacts_dir: Path) -> LoopState:
    """Load persisted loop state, or return a fresh state if missing."""
    state_file = artifacts_dir / f"pr-loop-{pr_number}.json"
    if not state_file.exists():
        return LoopState(pr_number=pr_number, round=1, status=LoopExitStatus.RUNNING)
    try:
        data = state_file.read_text(encoding="utf-8")
        return LoopState.model_validate_json(data)
    except (json.JSONDecodeError, ValueError) as exc:
        raise LoopStateError(f"Corrupted loop state file {state_file}: {exc}") from exc


def save_loop_state(state: LoopState, artifacts_dir: Path) -> None:
    """Persist loop state to work_artifacts/pr-loop-<PR>.json."""
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    state_file = artifacts_dir / f"pr-loop-{state.pr_number}.json"
    state_file.write_text(state.model_dump_json(indent=2), encoding="utf-8")
