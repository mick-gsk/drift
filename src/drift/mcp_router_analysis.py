"""Bounded-context router for scan/diff/nudge MCP tool implementations."""

from __future__ import annotations

import asyncio
import contextlib
import io
import json
from typing import Any, cast

from drift.mcp_enrichment import _enrich_response_with_session
from drift.mcp_orchestration import (
    _resolve_diagnostic_hypothesis_context,
    _resolve_session,
    _session_defaults,
    _strict_guardrail_block_response,
    _trace_meta_from_hypothesis_result,
    _update_session_from_diff,
    _update_session_from_scan,
)


def _parse_csv_ids(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    values = [part.strip() for part in raw.split(",") if part.strip()]
    return values or None


async def _run_sync_in_thread(fn: Any, *args: object) -> Any:
    return await asyncio.to_thread(fn, *args)


async def _run_api_tool(tool_name: str, api_fn: Any, **kwargs: Any) -> str:
    def _sync() -> str:
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                result = api_fn(**kwargs)
            return json.dumps(result, default=str)
        except Exception as exc:
            from drift.api_helpers import _error_response

            error = _error_response("DRIFT-5001", str(exc), recoverable=True)
            error["tool"] = tool_name
            return json.dumps(error, default=str)

    return cast(str, await _run_sync_in_thread(_sync))


async def run_scan(
    *,
    path: str,
    target_path: str | None,
    since_days: int,
    signals: str | None,
    exclude_signals: str | None,
    max_findings: int,
    max_per_signal: int | None,
    response_detail: str,
    include_non_operational: bool,
    response_profile: str | None,
    session_id: str,
) -> str:
    from drift.api import scan

    session = _resolve_session(session_id)
    kwargs = _session_defaults(
        session,
        {
            "path": path,
            "target_path": target_path,
            "signals": _parse_csv_ids(signals),
            "exclude_signals": _parse_csv_ids(exclude_signals),
        },
    )

    try:
        raw = await _run_api_tool(
            "drift_scan",
            scan,
            path=kwargs["path"],
            target_path=kwargs["target_path"],
            since_days=since_days,
            signals=kwargs["signals"],
            exclude_signals=kwargs["exclude_signals"],
            max_findings=max_findings,
            max_per_signal=max_per_signal,
            response_detail=response_detail,
            include_non_operational=include_non_operational,
            response_profile=response_profile,
        )
        if session:
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                _update_session_from_scan(session, json.loads(raw))
        return _enrich_response_with_session(raw, session, "drift_scan")
    except Exception as exc:
        from drift.api_helpers import _error_response

        error = _error_response("DRIFT-5001", str(exc), recoverable=True)
        error["tool"] = "drift_scan"
        return json.dumps(error, default=str)


async def run_diff(
    *,
    path: str,
    diff_ref: str,
    uncommitted: bool,
    staged_only: bool,
    baseline_file: str | None,
    max_findings: int,
    response_detail: str,
    signals: str | None,
    exclude_signals: str | None,
    response_profile: str | None,
    hypothesis_id: str | None,
    diagnostic_hypothesis: Any,
    session_id: str,
) -> str:
    from drift.api import diff

    session = _resolve_session(session_id)
    blocked = _strict_guardrail_block_response("drift_diff", session)
    if blocked is not None:
        return blocked
    hypothesis_ctx = _resolve_diagnostic_hypothesis_context(
        tool_name="drift_diff",
        session=session,
        hypothesis_id=hypothesis_id,
        diagnostic_hypothesis=diagnostic_hypothesis,
    )
    if hypothesis_ctx.get("blocked_response"):
        return cast(str, hypothesis_ctx["blocked_response"])
    kwargs = _session_defaults(
        session,
        {
            "path": path,
            "signals": _parse_csv_ids(signals),
            "exclude_signals": _parse_csv_ids(exclude_signals),
        },
    )
    bl_file = baseline_file
    if bl_file is None and session and session.baseline_file:
        bl_file = session.baseline_file

    raw = await _run_api_tool(
        "drift_diff",
        diff,
        path=kwargs["path"],
        diff_ref=diff_ref,
        uncommitted=uncommitted,
        staged_only=staged_only,
        baseline_file=bl_file,
        max_findings=max_findings,
        response_detail=response_detail,
        signals=kwargs["signals"],
        exclude_signals=kwargs["exclude_signals"],
        response_profile=response_profile,
    )
    if session:
        with contextlib.suppress(json.JSONDecodeError, TypeError):
            _update_session_from_diff(session, json.loads(raw))
    with contextlib.suppress(json.JSONDecodeError, TypeError):
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            h_id = cast(str | None, hypothesis_ctx.get("hypothesis_id"))
            if h_id:
                parsed["hypothesis_id"] = h_id
                parsed["verification_evidence"] = {
                    "tool": "drift_diff",
                    "accept_change": parsed.get("accept_change"),
                    "blocking_reasons": parsed.get("blocking_reasons", []),
                }
                raw = json.dumps(parsed, default=str)
    return _enrich_response_with_session(
        raw,
        session,
        "drift_diff",
        trace_meta=_trace_meta_from_hypothesis_result("drift_diff", raw),
    )


async def run_nudge(
    *,
    path: str,
    changed_files: str | None,
    uncommitted: bool,
    response_profile: str | None,
    hypothesis_id: str | None,
    diagnostic_hypothesis: Any,
    session_id: str,
    task_signal: str | None,
    task_edit_kind: str | None,
    task_context_class: str | None,
) -> str:
    from drift.api import nudge

    session = _resolve_session(session_id)
    blocked = _strict_guardrail_block_response("drift_nudge", session)
    if blocked is not None:
        return blocked
    hypothesis_ctx = _resolve_diagnostic_hypothesis_context(
        tool_name="drift_nudge",
        session=session,
        hypothesis_id=hypothesis_id,
        diagnostic_hypothesis=diagnostic_hypothesis,
    )
    if hypothesis_ctx.get("blocked_response"):
        return cast(str, hypothesis_ctx["blocked_response"])
    resolved_path = path
    if session and (not path or path == "."):
        resolved_path = session.repo_path

    raw = await _run_api_tool(
        "drift_nudge",
        nudge,
        path=resolved_path,
        changed_files=_parse_csv_ids(changed_files),
        uncommitted=uncommitted,
        response_profile=response_profile,
        task_signal=task_signal,
        task_edit_kind=task_edit_kind,
        task_context_class=task_context_class,
    )
    if session:
        try:
            result = json.loads(raw)
            score = result.get("score")
            if score is not None:
                session.last_scan_score = score
        except (json.JSONDecodeError, TypeError):
            pass
        session.touch()
    with contextlib.suppress(json.JSONDecodeError, TypeError):
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            h_id = cast(str | None, hypothesis_ctx.get("hypothesis_id"))
            if h_id:
                parsed["hypothesis_id"] = h_id
                parsed["verification_evidence"] = {
                    "tool": "drift_nudge",
                    "safe_to_commit": parsed.get("safe_to_commit"),
                    "blocking_reasons": parsed.get("blocking_reasons", []),
                    "changed_files": parsed.get("changed_files", []),
                }
                raw = json.dumps(parsed, default=str)
    return _enrich_response_with_session(
        raw,
        session,
        "drift_nudge",
        trace_meta=_trace_meta_from_hypothesis_result("drift_nudge", raw),
    )
