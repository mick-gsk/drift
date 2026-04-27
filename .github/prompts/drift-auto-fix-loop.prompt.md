---
name: drift-auto-fix-loop
description: >
  Use after `/drift-fix-plan` to enter a guided, one-finding-at-a-time auto-fix
  loop. Presents each finding with an explicit confirm/skip gate before applying
  changes, tracks applied vs. skipped findings in a running summary, and offers
  `/drift-export-report` when the loop completes.
---

# Drift: Auto-Fix Loop

Step through each finding from the drift fix plan one at a time. For every finding
you receive a description of the problem, a proposed code change, and an explicit
confirm/skip gate — nothing is applied without your approval. At the end, a summary
shows which findings were fixed and which were skipped.

Run `/drift-fix-plan` first to generate the task list before starting this loop.

## Context

Read `.vscode/drift-session.json`.
If the file does not exist: stop and prompt the user to run `drift analyze` first.
If `analyzed_at` is older than 24 hours: warn with the session age and recommend re-analysis. Do not block.

## Workflow

1. Parse `.vscode/drift-session.json` and reconstruct the ordered fix task list
   (from `top_findings`, sorted critical → high → medium → low).
2. For each task, in order:
   a. Display: signal type, severity, file, line range, reason.
   b. Propose a concrete code edit (diff or inline suggestion).
   c. **Gate** — ask the user: `Apply this fix? [yes / skip / stop]`.
      - `yes` → apply the edit, mark the finding as **fixed**.
      - `skip` → leave unchanged, mark as **skipped**.
      - `stop` → exit the loop immediately and go to step 3.
3. After all tasks (or on `stop`), display a **Loop Summary** table:
   `| Finding | Severity | File | Status (fixed / skipped) |`
4. Offer the next step prompt.

## Output

- **Applied edits**: inline code changes in the affected files.
- **Loop summary**: markdown table with fixed/skipped status per finding.

## Next Step

After completing this workflow, continue with:
- **[/drift-export-report]** — generate a shareable report of the current state.
