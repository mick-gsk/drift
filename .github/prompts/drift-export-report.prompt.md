---
name: drift-export-report
description: >
  Invoke after `drift analyze` (or after `/drift-fix-plan`) to generate a
  self-contained markdown report of all architectural findings, composite score,
  and recommended actions. The report is readable without drift knowledge and can
  be shared externally or attached to a ticket.
---

# Drift: Export Findings Report

Produce a self-contained, shareable markdown report from the most recent drift
analysis. The report includes the composite score, grade, all findings grouped by
severity, and recommended actions. It is intended for stakeholders who do not have
drift installed.

## Context

Read `.vscode/drift-session.json`.
If the file does not exist: stop and prompt the user to run `drift analyze` first.
If `analyzed_at` is older than 24 hours: warn with the session age and recommend re-analysis. Do not block.

## Workflow

1. Parse `.vscode/drift-session.json` and extract all fields.
2. Build a markdown document with the following sections:
   - **Header**: repository path, analysis timestamp, drift score, grade.
   - **Summary**: one-paragraph plain-language interpretation of the score and grade.
   - **Findings** (grouped by severity, critical → high → medium → low):
     - Signal type, file, line range, reason, suggested action.
   - **Metrics**: `findings_total`, `critical_count`, `high_count`.
   - **Recommendations**: top 3 actionable next steps derived from the findings.
3. If the session includes a completed fix plan (provided earlier in context), append a
   **Fix Plan** section summarising the planned repairs.
4. Write the report to `drift-report-<YYYY-MM-DD>.md` in the repository root, or offer
   to copy it to the clipboard if no write access is available.

## Output

- **Report file**: `drift-report-<YYYY-MM-DD>.md` in the repository root.
- **Confirmation message**: file path and word count.

## Next Step

After completing this workflow, continue with:
- **[/drift-auto-fix-loop]** — start applying the fixes described in the report.
