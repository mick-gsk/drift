"""Deprecated task-leasing MCP tools (multi-agent coordination).

These tools will be removed in v3.0.
Use ``drift_session_end(completed_tasks=[...])`` instead.

Moving them to this isolated module keeps mcp_server.py clean while
preserving backward compatibility until the planned removal.
"""

from __future__ import annotations

import json
from typing import Any

from drift.mcp_enrichment import _session_error_response

_TASK_DEPRECATION_MSG = (
    "DEPRECATED: Task leasing tools (drift_task_claim, drift_task_renew, "
    "drift_task_release, drift_task_complete, drift_task_status) will be "
    "removed in v3.0. Use drift_session_end(completed_tasks=[...]) instead."
)


async def run_task_claim(
    *,
    session_id: str,
    agent_id: str,
    task_id: str | None,
    lease_ttl_seconds: int,
    max_reclaim: int,
) -> str:
    """Claim a pending task from the session's fix-plan queue."""
    import warnings

    warnings.warn(_TASK_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
    from drift.session import SessionManager

    session = SessionManager.instance().get(session_id)
    if session is None:
        return _session_error_response(
            "DRIFT-6001",
            f"Session {session_id[:8]} not found or expired.",
            session_id,
        )

    claim = session.claim_task(
        agent_id=agent_id,
        task_id=task_id or None,
        lease_ttl_seconds=lease_ttl_seconds,
        max_reclaim=max_reclaim,
    )
    if claim is None:
        q = session.queue_status()
        result: dict[str, Any] = {
            "status": "no_tasks_available",
            "session_id": session_id,
            "pending_count": q["pending_count"],
            "claimed_count": q["claimed_count"],
            "completed_count": q["completed_count"],
            "failed_count": q["failed_count"],
            "agent_instruction": (
                "No pending tasks available in this session."
                " All tasks may be claimed, completed, or failed."
                " Call drift_task_status for a full queue overview."
            ),
        }
        return json.dumps(result, default=str)

    task_dict = claim["task"]
    lease_dict = claim["lease"]
    result = {
        "status": "claimed",
        "session_id": session_id,
        "task": task_dict,
        "lease": lease_dict,
        "agent_instruction": (
            f"Task {lease_dict['task_id']} claimed by {agent_id}."
            f" Lease expires in {lease_ttl_seconds}s."
            " Call drift_task_renew before expiry if more time is needed."
            " Call drift_task_complete when done, or drift_task_release to"
            " return the task to the pending pool."
        ),
    }
    return json.dumps(result, default=str)


async def run_task_renew(
    *,
    session_id: str,
    agent_id: str,
    task_id: str,
    extend_seconds: int,
) -> str:
    """Extend an active task lease to prevent it from expiring."""
    import warnings

    warnings.warn(_TASK_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
    from drift.session import SessionManager

    session = SessionManager.instance().get(session_id)
    if session is None:
        return _session_error_response(
            "DRIFT-6001",
            f"Session {session_id[:8]} not found or expired.",
            session_id,
        )

    outcome = session.renew_lease(
        agent_id=agent_id,
        task_id=task_id,
        extend_seconds=extend_seconds,
    )
    status = outcome.get("status", "not_found")
    if status == "renewed":
        outcome["session_id"] = session_id
        outcome["agent_instruction"] = (
            f"Lease for task {task_id} extended by {extend_seconds}s."
        )
    else:
        outcome["session_id"] = session_id
        outcome["agent_instruction"] = (
            outcome.get("error", "Renewal failed.")
            + " Call drift_task_status for current queue state."
        )
    return json.dumps(outcome, default=str)


async def run_task_release(
    *,
    session_id: str,
    agent_id: str,
    task_id: str,
    max_reclaim: int,
) -> str:
    """Release a claimed task back to the pending pool."""
    import warnings

    warnings.warn(_TASK_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
    from drift.session import SessionManager

    session = SessionManager.instance().get(session_id)
    if session is None:
        return _session_error_response(
            "DRIFT-6001",
            f"Session {session_id[:8]} not found or expired.",
            session_id,
        )

    outcome = session.release_task(
        agent_id=agent_id,
        task_id=task_id,
        max_reclaim=max_reclaim,
    )
    state = outcome.get("status", "released")
    if state == "released":
        agent_instruction = (
            f"Task {task_id} released back to the pending pool"
            f" (reclaim count: {outcome.get('reclaim_count', 0)})."
            " Another agent can now claim it."
        )
    elif state == "failed":
        agent_instruction = (
            f"Task {task_id} has reached max_reclaim={max_reclaim}"
            " and is now marked as failed. It will not be re-queued."
        )
    else:
        agent_instruction = (
            outcome.get("error", "Release failed.")
            + " Call drift_task_status for current queue state."
        )
    outcome["session_id"] = session_id
    outcome["agent_instruction"] = agent_instruction
    return json.dumps(outcome, default=str)


async def run_task_complete(
    *,
    session_id: str,
    agent_id: str,
    task_id: str,
    verify_evidence: Any,
) -> str:
    """Mark a claimed task as completed and release its lease."""
    import warnings

    warnings.warn(_TASK_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
    from drift.session import SessionManager

    session = SessionManager.instance().get(session_id)
    if session is None:
        return _session_error_response(
            "DRIFT-6001",
            f"Session {session_id[:8]} not found or expired.",
            session_id,
        )

    result = {"verify_evidence": verify_evidence} if verify_evidence is not None else None
    outcome = session.complete_task(agent_id=agent_id, task_id=task_id, result=result)
    state = outcome.get("status", "completed")
    if state == "completed":
        remaining = session.tasks_remaining()
        agent_instruction = f"Task {task_id} completed. {remaining} task(s) remaining."
        if remaining == 0:
            agent_instruction += (
                " All tasks done — call drift_session_end for final summary."
            )
    elif state == "already_completed":
        agent_instruction = f"Task {task_id} was already completed."
    elif state == "verify_plan_required":
        agent_instruction = (
            "Verification required before completing this task."
            " Call drift_nudge on the changed files first, then pass the result"
            " as verify_evidence (must contain safe_to_commit=true)."
        )
    else:
        agent_instruction = (
            outcome.get("error", "Completion failed.")
            + " Call drift_task_status for current queue state."
        )
    outcome["session_id"] = session_id
    outcome["tasks_remaining"] = session.tasks_remaining()
    outcome["agent_instruction"] = agent_instruction
    return json.dumps(outcome, default=str)


async def run_task_status(
    *,
    session_id: str,
) -> str:
    """Return a full queue overview: pending, claimed, completed, failed tasks."""
    import warnings

    warnings.warn(_TASK_DEPRECATION_MSG, DeprecationWarning, stacklevel=2)
    from drift.session import SessionManager

    session = SessionManager.instance().get(session_id)
    if session is None:
        return _session_error_response(
            "DRIFT-6001",
            f"Session {session_id[:8]} not found or expired.",
            session_id,
        )

    status = session.queue_status()
    status["session_id"] = session_id
    status["tasks_remaining"] = session.tasks_remaining()
    pending = status.get("pending_count", 0)
    claimed = status.get("claimed_count", 0)
    completed = status.get("completed_count", 0)
    failed = status.get("failed_count", 0)
    status["agent_instruction"] = (
        f"Queue: {pending} pending, {claimed} claimed,"
        f" {completed} completed, {failed} failed."
        + (
            " All tasks done — call drift_session_end."
            if pending == 0 and claimed == 0 and completed > 0
            else ""
        )
    )
    return json.dumps(status, default=str)
