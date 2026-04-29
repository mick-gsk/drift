---
name: drift-repo-quickscan
description: "One-shot architectural health check for any repo using drift-analyzer. Use when running drift for the first time on an unknown project, performing a quick first-look analysis, checking repo health without drift expertise, scanning a new codebase, or when someone asks 'is this repo worth analyzing'. No drift configuration or prior knowledge required."
---

# Drift Repo Quickscan

**Distributable skill — copy this file to `.github/skills/drift-repo-quickscan/SKILL.md` in any repository.**

Run a 5-minute architectural health check on any repo using drift-analyzer.
No config file, no prior drift knowledge, and no existing baseline needed.

For ongoing workflow, project-specific tuning, CI integration, and MCP usage,
see `drift-effective-usage` instead.

## Use When

- First contact with an unknown codebase
- Quick architecture review before starting a task
- Checking if a repo has structural problems worth addressing
- No `drift.yaml` or drift baseline exists yet
- User asks "is this repo in good shape?" or "what are the main problems here?"

## Phase 0 — Prerequisites

Check whether drift is installed:

```bash
pip show drift-analyzer
```

If not installed, offer two options:

```bash
# Permanent install (recommended)
pip install drift-analyzer

# Zero-install one-shot run (no global side effects)
uvx drift-analyzer analyze --repo . --format json --exit-zero
```

Proceed with whichever is available. Use `uvx` only if pip install is not an option.

## Phase 1 — Baseline Analysis

Run drift against the current repo. The `--exit-zero` flag ensures this never
interrupts the conversation even when findings exist.

```bash
drift analyze --repo . --format json --exit-zero
```

Parse the JSON output. Extract:
- `composite_score` — overall architectural health (0–100, lower = more erosion)
- `findings` array — sorted by severity
- `summary.signal_counts` — how many findings per signal type

If the JSON output contains non-JSON trailing text (Rich symbols), extract from the
first `{` to the last `}` before parsing.

## Phase 2 — Explain the Top 3 Findings

Take the three findings with the highest severity (critical → high → medium).
For each one, run:

```bash
drift explain <signal_id>
```

For example: `drift explain PFS`, `drift explain AVS`, `drift explain MDS`.

Do NOT explain all findings — three is enough for a first-look. The goal is a
clear mental model of the dominant issue, not an exhaustive audit.

## Phase 3 — Summary

Present a concise summary:

1. **Score:** `composite_score` with a plain-language band:
   - 80–100: healthy
   - 60–79: manageable erosion
   - 40–59: significant erosion, plan remediation
   - 0–39: severe erosion, prioritize immediately

2. **Dominant signal:** the signal_id with the most findings or highest severity.
   One sentence explaining what it means in practical terms for this repo.

3. **Severity distribution:** count of critical / high / medium / low findings.

4. **One concrete next action:** the single most actionable step based on the
   top finding. Be specific about which file or module to address first.

## Phase 4 — Optional: Persist Configuration

If the user wants to keep drift set up for ongoing use:

```bash
drift init --auto
```

This generates a `drift.yaml` tuned to the repo's language and structure.
The user can then run `drift analyze` any time without the `--exit-zero` flag.

Suggest this only after Phase 3. Do not run it automatically.

## Guardrails

- Do not interpret individual findings as certainties — drift detects structural
  patterns, not bugs. Present findings as signals worth investigating.
- Do not suggest removing files or refactoring code in Phase 2/3. Explain first,
  act only when the user explicitly asks.
- If `composite_score` is above 80 and there are no critical/high findings,
  say so clearly. Not every repo needs remediation work.
- If drift produces errors (missing git history, empty repo, parse errors),
  report the error text and suggest `drift analyze --repo . --no-git --exit-zero`
  as a fallback for repos without git history.
