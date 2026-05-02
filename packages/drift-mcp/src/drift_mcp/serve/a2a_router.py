"""A2A JSON-RPC 2.0 skill dispatcher for drift."""

from __future__ import annotations

import logging
import os
from typing import Any

from drift_mcp.serve.models import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    METHOD_NOT_FOUND,
    A2AErrorDetail,
    A2AErrorResponse,
    A2AMessage,
    A2AMessagePart,
    A2AMessageSendParams,
    A2AResponse,
    A2AResult,
)

logger = logging.getLogger(__name__)

# Mapping from A2A skill id → handler function
_SKILL_DISPATCH: dict[str, Any] = {}


def _ensure_dispatch_table() -> dict[str, Any]:
    """Lazily populate the dispatch table on first call."""
    if _SKILL_DISPATCH:
        return _SKILL_DISPATCH

    _SKILL_DISPATCH.update(
        {
            "scan": _handle_scan,
            "diff": _handle_diff,
            "explain": _handle_explain,
            "fix_plan": _handle_fix_plan,
            "validate": _handle_validate,
            "nudge": _handle_nudge,
            "brief": _handle_brief,
            "negative_context": _handle_negative_context,
            "compile_policy": _handle_compile_policy,
            "patch_begin": _handle_patch_begin,
            "patch_check": _handle_patch_check,
            "patch_commit": _handle_patch_commit,
            "capture_intent": _handle_capture_intent,
            "verify_intent": _handle_verify_intent,
            "feedback_for_agent": _handle_feedback_for_agent,
            "blast_radius": _handle_blast_radius,
        }
    )
    return _SKILL_DISPATCH


def _extract_skill_and_params(
    params: A2AMessageSendParams,
) -> tuple[str | None, dict[str, Any]]:
    """Extract skill id and parameters from an A2A message.

    Looks for ``skillId`` in message metadata first, then falls back to
    a ``data`` part with a ``skill`` field.

    Args:
        params: The A2A message send parameters.

    Returns:
        Tuple of (skill_id, skill_params).  skill_id is None if not found.
    """
    skill_id: str | None = None
    skill_params: dict[str, Any] = {}

    # Priority 1: metadata.skillId
    if params.message.metadata and "skillId" in params.message.metadata:
        skill_id = params.message.metadata["skillId"]

    # Priority 2: first data part with 'skill' key
    for part in params.message.parts:
        if part.kind == "data" and part.data and "skill" in part.data:
            if skill_id is None:
                skill_id = part.data["skill"]
            # Merge remaining keys as parameters
            skill_params.update(
                {k: v for k, v in part.data.items() if k != "skill"}
            )

    return skill_id, skill_params


def _validate_repo_path(path: str) -> str:
    """Validate and normalize a repository path.

    Prevents path traversal by resolving the path and ensuring it exists
    and is a directory.

    Args:
        path: Raw path string from the request.

    Returns:
        Resolved absolute path string.

    Raises:
        ValueError: If path does not exist or is not a directory.
    """
    resolved = os.path.realpath(os.path.normpath(path))
    if not os.path.isdir(resolved):
        msg = f"Repository path does not exist or is not a directory: {path}"
        raise ValueError(msg)
    return resolved


def dispatch(
    params: A2AMessageSendParams, request_id: str | int
) -> A2AResponse | A2AErrorResponse:
    """Dispatch an A2A message to the appropriate drift skill handler.

    Args:
        params: The parsed A2A message send parameters.
        request_id: The JSON-RPC request id for the response.

    Returns:
        An A2A success or error response.
    """
    table = _ensure_dispatch_table()
    skill_id, skill_params = _extract_skill_and_params(params)

    if skill_id is None:
        return A2AErrorResponse(
            id=request_id,
            error=A2AErrorDetail(
                code=INVALID_PARAMS,
                message=(
                    "Missing skill identifier. Provide 'skillId' in message "
                    "metadata or a data part with a 'skill' field."
                ),
            ),
        )

    handler = table.get(skill_id)
    if handler is None:
        return A2AErrorResponse(
            id=request_id,
            error=A2AErrorDetail(
                code=METHOD_NOT_FOUND,
                message=f"Unknown skill: {skill_id!r}",
                data={"available_skills": sorted(table.keys())},
            ),
        )

    try:
        result_data = handler(skill_params)
    except ValueError as exc:
        return A2AErrorResponse(
            id=request_id,
            error=A2AErrorDetail(
                code=INVALID_PARAMS,
                message=str(exc),
            ),
        )
    except Exception:
        logger.exception("Skill %r failed", skill_id)
        return A2AErrorResponse(
            id=request_id,
            error=A2AErrorDetail(
                code=INTERNAL_ERROR,
                message=f"Internal error executing skill {skill_id!r}.",
            ),
        )

    return A2AResponse(
        id=request_id,
        result=A2AResult(
            message=A2AMessage(
                role="agent",
                parts=[
                    A2AMessagePart(kind="data", data=result_data),
                ],
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Skill handlers — each lazily imports drift.api
# ---------------------------------------------------------------------------


def _handle_scan(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api import scan

    path = _validate_repo_path(params.get("path", "."))
    return scan(
        path=path,
        target_path=params.get("target_path"),
        response_detail=params.get("response_detail", "detailed"),
        since_days=params.get("since_days", 90),
        max_findings=int(params.get("max_findings", 10)),
        strategy=params.get("strategy", "diverse"),
    )


def _handle_diff(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api import diff

    path = _validate_repo_path(params.get("path", "."))
    baseline_file = params.get("baseline_file")
    uncommitted = params.get("uncommitted", False)
    diff_ref = params.get("diff_ref", "HEAD~1")
    return diff(
        path=path,
        baseline_file=baseline_file,
        uncommitted=uncommitted,
        diff_ref=diff_ref,
    )


def _handle_explain(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api import explain

    topic = params.get("topic")
    if not topic:
        msg = "Parameter 'topic' is required for explain skill."
        raise ValueError(msg)
    repo_path = params.get("path")
    if repo_path:
        repo_path = _validate_repo_path(repo_path)
    return explain(topic=topic, repo_path=repo_path)


def _handle_fix_plan(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api import fix_plan

    path = _validate_repo_path(params.get("path", "."))
    return fix_plan(
        path=path,
        max_tasks=params.get("max_tasks", 10),
    )


def _handle_validate(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api import validate

    path = _validate_repo_path(params.get("path", "."))
    return validate(path=path)


def _handle_nudge(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api import nudge

    path = _validate_repo_path(params.get("path", "."))
    return nudge(path=path)


def _handle_brief(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api import brief

    path = _validate_repo_path(params.get("path", "."))
    task = params.get("task", "")
    return brief(path=path, task=task)


def _handle_negative_context(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api import negative_context

    path = _validate_repo_path(params.get("path", "."))
    return negative_context(path=path)


def _handle_compile_policy(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api import compile_policy

    path = _validate_repo_path(params.get("path", "."))
    task = params.get("task", "")
    return compile_policy(
        path=path,
        task=task,
        task_spec_path=params.get("task_spec_path"),
        diff_ref=params.get("diff_ref"),
        max_rules=params.get("max_rules", 15),
    )


def _handle_patch_begin(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api import patch_begin

    return patch_begin(
        task_id=params["task_id"],
        declared_files=params.get("declared_files", []),
        expected_outcome=params.get("expected_outcome", ""),
        session_id=params.get("session_id"),
        blast_radius=params.get("blast_radius", "local"),
        forbidden_paths=params.get("forbidden_paths"),
        max_diff_lines=params.get("max_diff_lines"),
    )


def _handle_patch_check(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api import patch_check

    path = _validate_repo_path(params.get("path", "."))
    return patch_check(
        task_id=params["task_id"],
        declared_files=params.get("declared_files", []),
        path=path,
        forbidden_paths=params.get("forbidden_paths"),
        max_diff_lines=params.get("max_diff_lines"),
    )


def _handle_patch_commit(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api import patch_commit

    path = _validate_repo_path(params.get("path", "."))
    return patch_commit(
        task_id=params["task_id"],
        declared_files=params.get("declared_files", []),
        expected_outcome=params.get("expected_outcome", ""),
        path=path,
        session_id=params.get("session_id"),
    )


def _handle_capture_intent(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api.capture_intent import capture_intent

    raw = params.get("raw", "")
    path = params.get("path", ".")
    if not raw:
        msg = "Parameter 'raw' is required for capture_intent."
        raise ValueError(msg)
    return capture_intent(raw=raw, path=path)


def _handle_verify_intent(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api.verify_intent import verify_intent

    intent_id = params.get("intent_id", "")
    artifact_path = params.get("artifact_path", "")
    path = params.get("path", ".")
    if not intent_id:
        msg = "Parameter 'intent_id' is required for verify_intent."
        raise ValueError(msg)
    if not artifact_path:
        msg = "Parameter 'artifact_path' is required for verify_intent."
        raise ValueError(msg)
    return verify_intent(intent_id=intent_id, artifact_path=artifact_path, path=path)


def _handle_feedback_for_agent(params: dict[str, Any]) -> dict[str, Any]:
    from drift.api.feedback_for_agent import feedback_for_agent

    intent_id = params.get("intent_id", "")
    path = params.get("path", ".")
    artifact_path = params.get("artifact_path", "")
    if not intent_id:
        msg = "Parameter 'intent_id' is required for feedback_for_agent."
        raise ValueError(msg)
    if not artifact_path:
        msg = "Parameter 'artifact_path' is required for feedback_for_agent."
        raise ValueError(msg)
    return feedback_for_agent(intent_id=intent_id, path=path, artifact_path=artifact_path)


def _handle_blast_radius(params: dict[str, Any]) -> dict[str, Any]:
    """A2A-Handler für die Blast-Radius-Engine (ADR-087).

    Parameter (alle optional, Defaults konservativ):

    - ``path``: Repo-Root (default: ``"."``).
    - ``changed_files``: Liste POSIX-Pfade, die Git-Diff ersetzt.
    - ``ref``: Git-Basis-Ref (default: ``"HEAD"``).
    - ``head``: Git-HEAD (default: ``"HEAD"``).
    - ``include_skills``: Guard-Skill-Analyse aktivieren (default: True).
    - ``include_policy``: Policy-Gate-Impacts aktivieren (default: True).
    - ``persist``: Report auf Disk schreiben (default: False; Gate schreibt selbst).

    Schreibt **nie** Maintainer-Ack-Dateien.
    """
    from drift.blast_radius import compute_blast_report, save_blast_report
    from drift.blast_radius._change_detector import resolve_repo_path

    path = _validate_repo_path(params.get("path", "."))
    changed_files_raw = params.get("changed_files")
    changed_files: list[str] | None = None
    if changed_files_raw is not None:
        if not isinstance(changed_files_raw, list) or not all(
            isinstance(x, str) for x in changed_files_raw
        ):
            msg = "Parameter 'changed_files' must be a list of strings."
            raise ValueError(msg)
        changed_files = list(changed_files_raw)

    report = compute_blast_report(
        path,
        ref=str(params.get("ref", "HEAD")),
        head=str(params.get("head", "HEAD")),
        changed_files=changed_files,
        include_skills=bool(params.get("include_skills", True)),
        include_policy=bool(params.get("include_policy", True)),
    )

    result: dict[str, Any] = report.model_dump(mode="json")
    if bool(params.get("persist", False)):
        target = save_blast_report(resolve_repo_path(path), report)
        result["persisted_to"] = target.as_posix()

    # Kompakte Human-Summary ergänzen (Top-3 kritische Impacts)
    top = [
        {
            "kind": imp.kind.value,
            "severity": imp.severity.value,
            "target_id": imp.target_id,
            "reason": imp.reason,
        }
        for imp in report.impacts[:3]
    ]
    result["summary"] = {
        "impact_count": len(report.impacts),
        "requires_maintainer_ack": report.has_critical_impacts(),
        "critical_ids": list(report.critical_impact_ids()),
        "top_impacts": top,
        "degraded": report.degraded,
    }
    return result
