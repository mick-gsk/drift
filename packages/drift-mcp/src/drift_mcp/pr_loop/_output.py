"""Rich and JSON output rendering for the PR review loop (T035, T036)."""

from __future__ import annotations

import json

from drift_mcp.pr_loop._models import LoopExitStatus, LoopState, ReviewState


def render_rich(state: LoopState, pr_number: int) -> None:
    """Render per-round progress and final status using Rich-compatible output."""
    try:
        from rich.console import Console

        console = Console()
    except ImportError:
        console = None  # type: ignore[assignment]

    def _print(msg: str) -> None:
        if console:
            console.print(msg, markup=False)
        else:
            print(msg)

    _print(f"PR #{pr_number} — Agent Review Loop")
    _print("──────────────────────────")
    for rr in state.rounds:
        _print(f"\nRound {rr.round_number}")
        for verdict in rr.verdicts:
            icon = "✓" if verdict.state == ReviewState.APPROVED else "✗"
            _print(f"  {icon} {verdict.reviewer}: {verdict.state.value}")
        if rr.unresolved_comments:
            _print(f"  Unresolved comments: {len(rr.unresolved_comments)}")
    _print(f"\nLoop exited: {state.status.value}")


def render_json(state: LoopState, pr_number: int, reviewers: list[str]) -> str:
    """Return JSON string matching the CLI contract schema."""
    verdicts = []
    for rr in state.rounds:
        for v in rr.verdicts:
            verdicts.append(
                {
                    "reviewer": v.reviewer,
                    "state": v.state.value,
                    "round": rr.round_number,
                }
            )
    exit_code_map = {
        LoopExitStatus.APPROVED: 0,
        LoopExitStatus.ESCALATED: 1,
        LoopExitStatus.ERROR: 2,
        LoopExitStatus.RUNNING: 2,
    }
    unresolved = []
    if state.rounds:
        last = state.rounds[-1]
        unresolved = [
            {"id": c.id, "author": c.author, "body": c.body} for c in last.unresolved_comments
        ]
    payload = {
        "pr_number": pr_number,
        "status": state.status.value,
        "rounds_completed": len(state.rounds),
        "rounds_max": state.round - 1,
        "reviewers": reviewers,
        "verdicts": verdicts,
        "escalated": state.status == LoopExitStatus.ESCALATED,
        "unresolved_comments": unresolved,
        "exit_code": exit_code_map.get(state.status, 2),
        "loop_state_file": f"work_artifacts/pr-loop-{pr_number}.json",
    }
    return json.dumps(payload, indent=2)
