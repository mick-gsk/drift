"""MCP server instruction builder.

Contains the base instructions string, negative-context enrichment logic,
and the timeout helper for the drift MCP server.

Extracted from mcp_server.py as part of Issue #378 — further modularisation
of the MCP transport layer.  Import from here instead of from mcp_server.py.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# ---------------------------------------------------------------------------
# Negative-context timeout (env-configurable)
# ---------------------------------------------------------------------------


def _load_negative_context_timeout_seconds() -> float:
    """Resolve MCP timeout for drift_negative_context from environment."""
    raw = os.getenv("DRIFT_MCP_NEGATIVE_CONTEXT_TIMEOUT_SECONDS", "20")
    try:
        return max(0.0, float(raw))
    except (TypeError, ValueError):
        return 20.0


_NEGATIVE_CONTEXT_TIMEOUT_SECONDS = _load_negative_context_timeout_seconds()

# ---------------------------------------------------------------------------
# Dynamic instructions builder
# ---------------------------------------------------------------------------

_MAX_NEGATIVE_CONTEXT_BYTES = 10 * 1024  # 10 KB
_SAFE_DO_NOT_RE = re.compile(r"^[\w\s.,;:!?()\'\"/@#%&\-+=<>|\\\[\]{}~^`]{1,200}$")

_BASE_INSTRUCTIONS = (
    "Drift is a deterministic static analyzer that detects architectural "
    "erosion in Python codebases. Use these tools to analyze repositories "
    "for coherence problems like pattern fragmentation, layer violations, "
    "and near-duplicate code.\n\n"
    "Tool workflow:\n"
    "1. drift_validate — check config & environment before first analysis\n"
    "2. drift_brief — get a structural briefing BEFORE implementing a task "
    "(returns scope-aware guardrails as prompt constraints)\n"
    "3. drift_scan — assess overall architectural health\n"
    "4. drift_negative_context — get anti-patterns to avoid in new code\n"
    "5. drift_diff — detect regressions or verify completed batches\n"
    "6. drift_fix_plan — get actionable repair tasks with constraints\n"
    "7. drift_explain — understand unfamiliar signals or findings\n"
    "8. drift_nudge — fast directional feedback between edits "
    "(usable inside batches)\n\n"
    "IMPORTANT: When asked to implement a feature, add functionality, or make "
    'structural changes, call drift_brief(task="<task description>") FIRST '
    "before writing any code. Use the returned guardrails as constraints "
    "in your code generation. If the scope confidence is below 0.5, ask the "
    "user to specify a --scope path.\n\n"
    "FEEDBACK LOOP ROLES:\n"
    "- drift_nudge = fast inner loop (use between edits, even inside a batch)\n"
    "- drift_diff  = full verification outer loop (use after completing a "
    "batch or before committing)\n"
    "Every response includes an 'agent_instruction' field — follow it.\n\n"
    "FIX-LOOP PROTOCOL (when fixing multiple findings):\n"
    '0. SESSION START: Call drift_session_start(path=".", autopilot=true) '
    "— this single call runs validate → brief → scan → fix_plan and "
    "returns combined results, saving 4 round-trips.\n"
    "1. TASK LOOP: Take the first task from the fix_plan result. Fix it. "
    'Call drift_nudge(session_id=sid, changed_files="path/to/file.py") '
    "for fast feedback (~0.2s). If direction=degrading, revert and retry.\n"
    "   NOTE on latency: if latency_exceeded=true AND baseline_created=true, "
    "this was a one-time cold-start cost — do NOT skip subsequent nudge calls. "
    "Only skip further nudge calls when latency_exceeded=true AND "
    "baseline_created=false (genuinely slow system).\n"
    "2. NEXT TASK: Call drift_fix_plan(session_id=sid, max_tasks=1) to get "
    "the next task. Repeat step 1.\n"
    "3. BATCH AWARENESS: Tasks with batch_eligible=true share a fix pattern. "
    "Apply the fix to ALL affected_files_for_pattern listed, not just the "
    "first. Use drift_nudge between edits for quick direction checks.\n"
    "4. VERIFICATION: After all tasks are done, call "
    "drift_diff(session_id=sid, uncommitted=True) once to verify.\n"
    "5. COMPLETED: When drift_diff shows 0 new findings, session is done.\n\n"
    "CRITICAL RULES:\n"
    "- Always use autopilot=true in session_start (saves 4 round-trips)\n"
    "- Always pass session_id to every tool call\n"
    "- In the fix loop, use max_tasks=1 for each subsequent task request. "
    "For the initial overview, follow the max_tasks value from the scan "
    "agent_instruction (autopilot handles this automatically).\n"
    "- Use drift_nudge (not drift_scan) after each file edit\n"
    "- Use drift_diff only once at the end, not after every edit\n"
    "- Follow agent_instruction and next_tool_call from every response\n\n"
    "BATCH REPAIR MODE:\n"
    "When fixing drift findings, apply the same fix pattern across "
    "multiple files in one iteration for batch_eligible tasks.\n"
    "Rules: Only batch fixes where batch_eligible=true in fix_plan response. "
    "Apply the SAME fix template to ALL affected_files_for_pattern. "
    "Verify the batch with a single drift_diff call, not per-file. "
    "If any file in the batch fails verification, revert that file only.\n\n"
    "SESSION WORKFLOW (recommended for multi-step tasks):\n"
    '1. drift_session_start(path=".", autopilot=true) → session_id '
    "(runs validate+brief+scan+fix_plan automatically)\n"
    "2. [fix loop: edit file → drift_nudge(session_id=sid) → check direction]\n"
    "3. drift_fix_plan(session_id=sid, max_tasks=1) → next task\n"
    "4. drift_diff(session_id=sid, uncommitted=True) → final verify\n"
    "5. drift_session_end(session_id=sid) → summary + cleanup\n"
    "Benefits: scope defaults carry across calls, scan results feed into "
    "fix_plan, guardrails persist, progress is tracked automatically."
)


def _load_negative_context_instructions() -> str:
    """Build MCP instructions, enriching with cached anti-patterns if available."""
    ctx_file = Path(".drift-negative-context.md")
    if not ctx_file.is_file():
        return _BASE_INSTRUCTIONS

    try:
        content = ctx_file.read_text(encoding="utf-8")
    except OSError:
        return _BASE_INSTRUCTIONS

    if len(content.encode("utf-8")) > _MAX_NEGATIVE_CONTEXT_BYTES:
        return _BASE_INSTRUCTIONS

    from drift.negative_context.export import MARKER_BEGIN, MARKER_END

    begin = content.find(MARKER_BEGIN)
    end = content.find(MARKER_END)
    if begin < 0 or end < 0:
        return _BASE_INSTRUCTIONS

    section = content[begin + len(MARKER_BEGIN) : end].strip()
    if not section:
        return _BASE_INSTRUCTIONS

    do_not_lines: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- **DO NOT:**"):
            candidate = stripped.removeprefix("- **DO NOT:** ")[:200]
            if _SAFE_DO_NOT_RE.match(candidate):
                do_not_lines.append(candidate)

    if not do_not_lines:
        return _BASE_INSTRUCTIONS

    top = do_not_lines[:10]
    suffix = f"\n  ... and {len(do_not_lines) - 10} more" if len(do_not_lines) > 10 else ""

    anti_pattern_block = (
        "\n\nKNOWN ANTI-PATTERNS IN THIS REPOSITORY "
        "(from last drift export-context):\n"
        + "\n".join(f"- DO NOT: {line}" for line in top)
        + suffix
    )

    return _BASE_INSTRUCTIONS + anti_pattern_block
