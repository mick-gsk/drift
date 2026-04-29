# Research: VS Code Copilot Chat Workflow Integration

**Phase**: 0 — Pre-Design Research  
**Feature**: `002-vscode-copilot-workflow`  
**Date**: 2026-04-27

---

## 1. HandoffBlock Injection Point (Rich Output)

**Decision**: Inject after `_render_analysis_details()` returns, before `_run_interactive_review()`, gated on `output_format == "rich" and not quiet`.

**Rationale**: This is the last user-visible Rich block before optional interactive review. It follows the existing pattern of `render_recommendations()` and `render_feedback_calibration_hint()` — both are appended after the main findings table. HandoffBlock is the final block the developer sees before the terminal prompt returns.

**Alternatives considered**:
- Inside `_render_analysis_details()` — rejected: that function already has a clear responsibility boundary (findings + recommendations); mixing in session I/O violates Single Responsibility.
- At the very end of `analyze()` after severity gate — rejected: the gate may `sys.exit()`, so the HandoffBlock would be skipped on failure.

---

## 2. HandoffBlock Injection Point (JSON Output)

**Decision**: Add an optional `copilot_handoff: dict | None = None` parameter to `analysis_to_json()` in `src/drift/output/json_output.py`. The caller (`render_or_emit_output`) receives it via a new optional kwarg and passes it through. If `None`, the key is omitted (backward compatible).

**Rationale**: The JSON dict is built in one place (`analysis_to_json`) before serialization. Injecting at that layer keeps the JSON output self-contained and testable without CLI invocation. Adding an optional key never breaks existing consumers.

**Alternatives considered**:
- Post-process the serialized JSON string in `analyze.py` — rejected: string manipulation of JSON is fragile and violates Library-First (core logic in CLI layer).
- New `analysis_to_json_with_handoff()` function — rejected: duplication; optional param is simpler and YAGNI-aligned.

---

## 3. Session File Write Point

**Decision**: Write `.vscode/drift-session.json` unconditionally after `save_last_scan()`, regardless of output format. Skip if `output_file` is explicitly set (because then the user is redirecting output, not doing an interactive session).

**Rationale**: The session file is about persisting context for Copilot Chat — it should be written even when the developer uses `--format json` in their editor extension. Skipping on `--output-file` avoids writing a session during automated export pipelines.

**Alternatives considered**:
- Only write when `output_format == "rich"` — rejected: a developer using `drift analyze --format json` in VS Code would lose the Copilot handoff.
- Gated on `not quiet` — rejected: quiet mode suppresses terminal output, not the session file; context persistence is silent-safe.

---

## 4. chat.promptFilesLocations Format

**Decision**: `"chat.promptFilesLocations": [".github/prompts/"]` added to `.vscode/settings.json`.

**Rationale**: VS Code 1.90+ supports `chat.promptFilesLocations` as an array of glob or relative paths. The existing `.github/prompts/` directory already contains drift prompt files; adding it to locations makes all `*.prompt.md` files discoverable as `/command-name` slash commands in Copilot Chat.

**Current state**: `.vscode/settings.json` has `chat.promptFilesRecommendations` but not `chat.promptFilesLocations`. The new key is additive — no existing key is changed.

**Alternatives considered**:
- Use `chat.promptFilesRecommendations` only — rejected: that controls UI suggestions, not discovery; the prompts are not invocable as slash commands without `chat.promptFilesLocations`.

---

## 5. Staleness Check Location

**Decision**: Staleness check lives in the `.prompt.md` files as natural-language instructions to the Copilot agent, not in Python code. Each prompt begins: "Read `.vscode/drift-session.json`. If the `analyzed_at` timestamp is older than 24 hours, show a warning with the session age and recommend re-running `drift analyze`. Do not block continuation."

**Rationale**: The prompts run in Copilot Chat, not in the Python process. Python code cannot gate a Copilot Chat session. The staleness logic belongs in the prompt layer, which is the correct execution boundary.

**Alternatives considered**:
- Python-side staleness field in JSON output — rejected: the session file is written by Python but read by Copilot; Python doesn't know when the prompt is opened.

---

## 6. .gitignore Entry

**Decision**: Add `.vscode/drift-session.json` to `.gitignore`.

**Current state**: `.gitignore` already contains `.vscode/` as a partial exclusion pattern (verify at implementation time). If not, add a specific entry to avoid excluding other committed `.vscode/` files (e.g., `settings.json`, `mcp.json`).

**Rationale**: `settings.json` and `mcp.json` are deliberately committed. A blanket `.vscode/` exclusion would be wrong. The entry must be specific: `.vscode/drift-session.json`.

---

## 7. Existing Prompt Pattern Reference

The existing `drift-fix-loop.prompt.md` provides the implementation pattern:
- YAML frontmatter: `name`, `description`
- H1 title + purpose paragraph
- References section (relevant skills/instructions)
- Numbered workflow steps with `drift_*` MCP tool calls
- Explicit stop condition

New prompts (`drift-fix-plan`, `drift-export-report`, `drift-auto-fix-loop`) MUST follow this structure and end with a "next step" handoff reference per FR-008.

---

## 8. Technology Stack (from Constitution)

All resolved — no clarifications needed:

| Aspect | Value |
|--------|-------|
| Language | Python 3.11+ |
| Models | Pydantic `frozen=True` |
| Terminal output | Rich `Panel`, `Text` |
| CLI | Click (no new subcommand needed) |
| Testing | pytest, TDD cycle enforced |
| Lint/types | ruff + mypy strict |

---

## Summary: All NEEDS CLARIFICATION Resolved

| Question | Decision |
|----------|----------|
| Rich injection point | After `_render_analysis_details()`, before `_run_interactive_review()` |
| JSON injection point | Optional param in `analysis_to_json()`, passed through `render_or_emit_output()` |
| Session write trigger | After `save_last_scan()`, skip if `output_file` set |
| Staleness check | In prompt files (natural language), not Python |
| settings.json key | `chat.promptFilesLocations: [".github/prompts/"]` |
| .gitignore scope | Specific: `.vscode/drift-session.json` |
