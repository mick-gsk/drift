"""Autopilot pipeline helpers for MCP session start (ADR-025 Phase D).

Contains the building blocks for the compact ``autopilot=true`` payload
that ``drift_session_start`` returns after running
validate → brief → scan → fix_plan automatically.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

AUTOPILOT_PAYLOAD_MODES: frozenset[str] = frozenset({"summary", "full"})
_AUTOPILOT_PREVIEW_LIMIT = 3


# ---------------------------------------------------------------------------
# Internal helpers — payload building
# ---------------------------------------------------------------------------


def _payload_checksum(payload: Any) -> str:
    """Return a stable 16-char hex checksum for on-demand payload references."""
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _autopilot_scan_finding_preview(item: dict[str, Any]) -> dict[str, Any]:
    """Return a slim finding preview entry for summary autopilot payloads."""
    return {
        "finding_id": item.get("finding_id"),
        "signal": item.get("signal") or item.get("signal_abbrev"),
        "severity": item.get("severity"),
        "title": item.get("title"),
        "file": item.get("file"),
        "line": item.get("line") or item.get("start_line"),
    }


def _autopilot_task_preview(item: dict[str, Any]) -> dict[str, Any]:
    """Return a slim fix-plan task preview entry for summary autopilot payloads."""
    metadata_raw = item.get("metadata")
    metadata: dict[str, Any] = metadata_raw if isinstance(metadata_raw, dict) else {}
    return {
        "id": item.get("id"),
        "signal": item.get("signal") or item.get("signal_abbrev"),
        "severity": item.get("severity"),
        "title": item.get("title"),
        "file": item.get("file") or item.get("file_path"),
        "start_line": item.get("start_line"),
        "batch_eligible": bool(item.get("batch_eligible") or metadata.get("batch_eligible")),
    }


def _autopilot_refs(
    *,
    session_id: str,
    validate_result: dict[str, Any],
    brief_result: dict[str, Any],
    scan_result: dict[str, Any],
    fix_plan_result: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Return on-demand references and checksums for heavy autopilot payload sections."""
    return {
        "validate": {
            "tool": "drift_validate",
            "params": {"session_id": session_id},
            "checksum": _payload_checksum(validate_result),
        },
        "brief": {
            "tool": "drift_brief",
            "params": {"session_id": session_id},
            "checksum": _payload_checksum(brief_result),
        },
        "scan": {
            "tool": "drift_scan",
            "params": {"session_id": session_id},
            "checksum": _payload_checksum(scan_result),
        },
        "fix_plan": {
            "tool": "drift_fix_plan",
            "params": {"session_id": session_id},
            "checksum": _payload_checksum(fix_plan_result),
        },
    }


def build_autopilot_summary(
    *,
    session_id: str,
    validate_result: dict[str, Any],
    brief_result: dict[str, Any],
    scan_result: dict[str, Any],
    fix_plan_result: dict[str, Any],
) -> dict[str, Any]:
    """Build compact default autopilot payload with previews and references."""
    finding_items_raw = scan_result.get("findings")
    task_items_raw = fix_plan_result.get("tasks")
    guardrail_items_raw = brief_result.get("guardrails")

    finding_items = finding_items_raw if isinstance(finding_items_raw, list) else []
    task_items = task_items_raw if isinstance(task_items_raw, list) else []
    guardrail_items = guardrail_items_raw if isinstance(guardrail_items_raw, list) else []

    finding_preview = [
        _autopilot_scan_finding_preview(item)
        for item in finding_items[:_AUTOPILOT_PREVIEW_LIMIT]
        if isinstance(item, dict)
    ]
    task_preview = [
        _autopilot_task_preview(item)
        for item in task_items[:_AUTOPILOT_PREVIEW_LIMIT]
        if isinstance(item, dict)
    ]
    guardrail_preview = guardrail_items[:_AUTOPILOT_PREVIEW_LIMIT]

    top_signals_raw = scan_result.get("top_signals")
    top_signals = [
        {
            "signal": item.get("signal"),
            "score": item.get("score"),
            "finding_count": item.get("finding_count"),
        }
        for item in (top_signals_raw if isinstance(top_signals_raw, list) else [])[:3]
        if isinstance(item, dict)
    ]

    total_finding_count = scan_result.get("total_finding_count")
    if not isinstance(total_finding_count, int):
        total_finding_count = int(scan_result.get("finding_count", len(finding_items)))

    total_task_count = fix_plan_result.get("total_available")
    if not isinstance(total_task_count, int):
        total_task_count = int(fix_plan_result.get("task_count", len(task_items)))

    return {
        "mode": "summary",
        "drift_score": scan_result.get("drift_score"),
        "task_count": total_task_count,
        "top_signals": top_signals,
        "next_tool_call": {
            "tool": "drift_fix_plan",
            "params": {"session_id": session_id},
        },
        "patch_protocol": {
            "steps": [
                "drift_patch_begin(task_id=<id>, declared_files=[...], expected_outcome=...)",
                "drift_patch_check(task_id=<id>, declared_files=[...])",
                "drift_patch_commit(task_id=<id>)",
            ],
            "when": "before_editing",
            "reference": "ADR-074",
        },
        "findings_preview": {
            "items": finding_preview,
            "count": len(finding_preview),
            "total_available": total_finding_count,
        },
        "tasks_preview": {
            "items": task_preview,
            "count": len(task_preview),
            "total_available": total_task_count,
        },
        "guardrails_preview": {
            "items": guardrail_preview,
            "count": len(guardrail_preview),
            "total_available": len(guardrail_items),
        },
        "payload_refs": _autopilot_refs(
            session_id=session_id,
            validate_result=validate_result,
            brief_result=brief_result,
            scan_result=scan_result,
            fix_plan_result=fix_plan_result,
        ),
    }
