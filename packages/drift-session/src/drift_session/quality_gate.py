"""Quality-drift detection between analysis runs.

Compares two run snapshots and classifies the trajectory
as *improving*, *stable*, or *degrading*, with an actionable advisory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from drift.remediation_activity import has_remediation_activity


@dataclass(frozen=True, slots=True)
class RunSnapshot:
    """Minimal snapshot of a single analysis run.

    Attributes:
        score: Composite drift score (0–100, lower is better).
        finding_count: Total number of findings.
        tool_calls: Number of tool calls at time of snapshot.
    """

    score: float
    finding_count: int
    tool_calls: int = 0


@dataclass(frozen=True, slots=True)
class QualityDrift:
    """Result of comparing two run snapshots.

    Attributes:
        direction: ``improving``, ``stable``, or ``degrading``.
        score_delta: Change in score (negative = improving).
        finding_delta: Change in finding count (negative = improving).
        advisory: Human-readable guidance for the agent.
    """

    direction: str  # "improving" | "stable" | "degrading"
    score_delta: float
    finding_delta: int
    advisory: str


@dataclass(frozen=True, slots=True)
class TrendGateDecision:
    """Decision payload for trend-gate enforcement."""

    blocked: bool
    reason: str
    score_delta: float
    window_commits: int
    remediation_activity_detected: bool
    history_points: int


# Thresholds below which changes are considered noise.
_SCORE_TOLERANCE = 0.5
_FINDING_TOLERANCE = 0


def compare_runs(
    before: RunSnapshot,
    after: RunSnapshot,
    *,
    score_tolerance: float = _SCORE_TOLERANCE,
    finding_tolerance: int = _FINDING_TOLERANCE,
) -> QualityDrift:
    """Compare two snapshots and return a quality-drift assessment.

    Args:
        before: Earlier run snapshot.
        after: Later run snapshot.
        score_tolerance: Absolute score delta that is still treated as stable.
        finding_tolerance: Absolute finding-count delta that is still treated as stable.
    """
    score_delta = round(after.score - before.score, 2)
    finding_delta = after.finding_count - before.finding_count

    # Classify direction
    if score_delta < -score_tolerance or finding_delta < -finding_tolerance:
        direction = "improving"
    elif score_delta > score_tolerance or finding_delta > finding_tolerance:
        direction = "degrading"
    else:
        direction = "stable"

    advisory = _build_advisory(direction, score_delta, finding_delta, after.tool_calls)

    return QualityDrift(
        direction=direction,
        score_delta=score_delta,
        finding_delta=finding_delta,
        advisory=advisory,
    )


def _build_advisory(
    direction: str, score_delta: float, finding_delta: int, tool_calls: int
) -> str:
    if direction == "improving":
        return (
            f"Score improved by {abs(score_delta):.1f} points, "
            f"{abs(finding_delta)} fewer findings. Keep going."
        )
    if direction == "degrading":
        return (
            f"Score worsened by {score_delta:.1f} points, "
            f"{finding_delta} more findings. "
            "Consider reverting recent changes or running drift_explain."
        )
    return "Score and findings stable. Proceed with next task."


def quality_drift_from_history(
    run_history: list[dict[str, Any]],
    *,
    score_tolerance: float = _SCORE_TOLERANCE,
    finding_tolerance: int = _FINDING_TOLERANCE,
) -> QualityDrift | None:
    """Compare the last two entries in a run history list.

    Returns ``None`` if fewer than two snapshots exist.
    """
    if len(run_history) < 2:
        return None
    prev = run_history[-2]
    curr = run_history[-1]
    required = ("score", "finding_count")
    for idx, entry in ((len(run_history) - 2, prev), (len(run_history) - 1, curr)):
        missing = [k for k in required if k not in entry]
        if missing:
            raise ValueError(
                f"run_history[{idx}] is missing required keys: {missing!r}"
            )
    return compare_runs(
        RunSnapshot(
            score=prev["score"],
            finding_count=prev["finding_count"],
            tool_calls=prev.get("tool_calls_at", 0),
        ),
        RunSnapshot(
            score=curr["score"],
            finding_count=curr["finding_count"],
            tool_calls=curr.get("tool_calls_at", 0),
        ),
        score_tolerance=score_tolerance,
        finding_tolerance=finding_tolerance,
    )


def _trend_snapshot_score(snapshot: dict[str, Any]) -> float | None:
    score = snapshot.get("drift_score")
    if isinstance(score, (int, float)):
        return float(score)
    return None


def _trend_commit_key(snapshot: dict[str, Any], index: int) -> str:
    commit_hash = snapshot.get("commit_hash")
    if isinstance(commit_hash, str) and commit_hash.strip():
        return f"commit:{commit_hash.strip()}"
    return f"run:{index}"


def _last_commit_window(
    snapshots: list[dict[str, Any]],
    *,
    window_commits: int,
) -> list[dict[str, Any]]:
    valid = [s for s in snapshots if _trend_snapshot_score(s) is not None]
    if not valid:
        return []

    selected_rev: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index in range(len(valid) - 1, -1, -1):
        snap = valid[index]
        commit_key = _trend_commit_key(snap, index)
        if commit_key in seen:
            continue
        seen.add(commit_key)
        selected_rev.append(snap)
        if len(selected_rev) >= window_commits:
            break

    selected_rev.reverse()
    return selected_rev


def evaluate_trend_gate(
    *,
    snapshots: list[dict[str, Any]],
    window_commits: int,
    delta_threshold: float,
    require_remediation_activity: bool,
) -> TrendGateDecision:
    """Evaluate trend-gate blocking logic for a commit window.

    Gate condition:
        score_delta >= delta_threshold over N commits AND
        (if enabled) no remediation activity was detected in the same window.
    """
    if window_commits < 2:
        raise ValueError("window_commits must be >= 2")

    window = _last_commit_window(snapshots, window_commits=window_commits)
    if len(window) < window_commits:
        return TrendGateDecision(
            blocked=False,
            reason="insufficient_history",
            score_delta=0.0,
            window_commits=window_commits,
            remediation_activity_detected=False,
            history_points=len(window),
        )

    first_score = _trend_snapshot_score(window[0])
    last_score = _trend_snapshot_score(window[-1])
    if first_score is None or last_score is None:
        return TrendGateDecision(
            blocked=False,
            reason="insufficient_history",
            score_delta=0.0,
            window_commits=window_commits,
            remediation_activity_detected=False,
            history_points=len(window),
        )

    score_delta = round(last_score - first_score, 4)
    if score_delta < delta_threshold:
        return TrendGateDecision(
            blocked=False,
            reason="below_delta_threshold",
            score_delta=score_delta,
            window_commits=window_commits,
            remediation_activity_detected=False,
            history_points=len(window),
        )

    remediation_detected = has_remediation_activity(window, window_commits=window_commits)

    if require_remediation_activity and remediation_detected:
        return TrendGateDecision(
            blocked=False,
            reason="remediation_detected",
            score_delta=score_delta,
            window_commits=window_commits,
            remediation_activity_detected=True,
            history_points=len(window),
        )

    return TrendGateDecision(
        blocked=True,
        reason=(
            "degradation_without_remediation"
            if require_remediation_activity
            else "degradation_threshold_exceeded"
        ),
        score_delta=score_delta,
        window_commits=window_commits,
        remediation_activity_detected=remediation_detected,
        history_points=len(window),
    )
