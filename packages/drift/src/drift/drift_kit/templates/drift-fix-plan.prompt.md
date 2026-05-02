---
name: drift-fix-plan
description: >
  Use after running `drift analyze` to generate a prioritized fix plan for the top
  architectural findings in your codebase. Reads `.vscode/drift-session.json` and
  produces actionable, ranked repair tasks with code-level guidance.
---

# Drift: Generate Fix Plan

Generate a prioritized, actionable fix plan from the most recent drift analysis.
Use this after `drift analyze` has run and `.vscode/drift-session.json` exists.
The plan ranks findings by severity and impact, and proposes concrete next steps
for each finding so you can start fixing immediately.

## Context

Read `.vscode/drift-session.json`.
If the file does not exist: tell the user to run `drift analyze --repo . --exit-zero` in the terminal
and then re-invoke this prompt. If a drift MCP server is available (`drift_scan` tool), call it
to run the analysis automatically, then re-read `.vscode/drift-session.json` before continuing.
If `analyzed_at` is older than 24 hours: warn with the session age and recommend re-analysis. Do not block.

## Workflow

1. Parse `.vscode/drift-session.json` and extract `top_findings`, `drift_score`, `grade`, and `findings_total`.
2. For each finding in `top_findings`, produce a numbered repair task containing:
   - **What**: the finding title and signal type.
   - **Where**: file path and line range (if available).
   - **Why**: the reason / root cause from the `reason` field.
   - **How**: a concrete code-level action (refactor, extract, move, rename, or remove).
   - **Effort**: estimated effort (low / medium / high).
3. Order tasks: critical findings first, then high, then medium/low. Within the same severity, order by impact descending.
4. Append a summary table: `| # | Signal | Severity | File | Effort |`.
5. Call `drift_fix_plan` via MCP (if available) to retrieve additional context and guardrails for each task.

## Output

- **Fix plan**: numbered task list (markdown), rendered in Copilot Chat.
- **Summary table**: one row per finding with severity and effort.
- _(Optional)_ Inline code snippets for straightforward refactors.

## Next Step

After completing this workflow, continue with:
- **[/drift-auto-fix-loop]** — step through each fix interactively with explicit confirm/skip gates.
