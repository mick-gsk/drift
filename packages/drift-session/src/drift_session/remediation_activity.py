"""Helpers for remediation-activity detection in trend-gate windows."""

from __future__ import annotations

from typing import Any


def finding_fingerprints(snapshot: dict[str, Any]) -> set[str]:
    """Return normalized finding fingerprints from a history snapshot."""
    raw = snapshot.get("finding_fingerprints")
    if not isinstance(raw, list):
        return set()
    return {fp for fp in raw if isinstance(fp, str) and fp}


def resolved_fingerprints(
    before_snapshot: dict[str, Any],
    after_snapshot: dict[str, Any],
) -> set[str]:
    """Return fingerprints present before and absent after."""
    before = finding_fingerprints(before_snapshot)
    after = finding_fingerprints(after_snapshot)
    return before - after


def has_remediation_activity(
    snapshots: list[dict[str, Any]],
    *,
    window_commits: int,
) -> bool:
    """Return True if at least one commit in the window resolves findings."""
    if window_commits < 2 or len(snapshots) < 2:
        return False

    for index in range(1, len(snapshots)):
        before = snapshots[index - 1]
        after = snapshots[index]

        before_commit = before.get("commit_hash")
        after_commit = after.get("commit_hash")
        if before_commit == after_commit and before_commit is not None:
            continue

        if resolved_fingerprints(before, after):
            return True

    return False
