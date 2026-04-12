# Drift MCP Autopilot — Copilot Agent Instructions

> Copy this file to `.github/copilot-instructions.md` in the target repository
> to enable autonomous drift fix-loop execution via Copilot Agent Mode.

## Workflow

You have access to the drift MCP server. Use it for all architectural analysis and repair.

### Session Protocol

1. **Start:** `drift_session_start(path=".", autopilot=true, ttl_seconds=3600)`
2. **Loop:** For each task:
   - `drift_task_claim(session_id, agent_id="copilot")` → get next task
   - Edit file(s) according to `task.action` and `task.constraints`
   - `drift_nudge(session_id, changed_files="<paths>")` → check direction
   - If `direction == "degrading"` and `safe_to_commit == false`: revert and retry once
   - `drift_task_complete(session_id, agent_id="copilot", task_id=...)` → mark done
3. **Verify:** `drift_diff(session_id, uncommitted=true)` → confirm `accept_change == true`
4. **End:** `drift_session_end(session_id)` → export summary
5. **Review:** Show `git diff --stat` — do NOT auto-commit, wait for user approval

### Rules

- Always pass `session_id` to every drift tool call
- Use `max_tasks=1` when requesting next tasks via `drift_fix_plan`
- For `batch_eligible` tasks: apply fix to ALL `affected_files_for_pattern`
- Use `drift_nudge` (not `drift_scan`) after each edit
- Use `drift_diff` only once at the end, not after every edit
- Follow `agent_instruction` and `next_tool_call` from every MCP response

### Audit Data Collection

After each `drift_task_complete`, record these fields for the final audit JSON:
- `task_id`, `signal`, `severity` (from task claim response)
- `fix_description` (from `task.action`)
- `affected_files` (from task or `affected_files_for_pattern`)
- `nudge_direction`, `nudge_delta` (from nudge response)

At the end, assemble `drift-audit.json` from collected data + `drift_session_end` response.
