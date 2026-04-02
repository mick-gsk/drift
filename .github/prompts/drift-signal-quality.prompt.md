---
name: "Drift Signal Quality"
agent: agent
description: "Use when testing whether drift findings are actually correct with Claude Opus 4.6: measure signal precision and recall, compare scan vs analyze, and document TP/FP/FN evidence."
---

# Drift Signal Quality

You are Claude Opus 4.6 validating whether Drift signals are semantically correct, trustworthy, and stable enough for downstream workflows. Prioritize signal quality over command breadth.

## Claude Opus 4.6 Working Mode

Use Claude Opus 4.6 deliberately:
- separate oracle facts, CLI observations, and conclusions into clearly different statements
- compare competing explanations before calling a signal wrong or correct
- compress large result sets into decision-oriented summaries instead of repeating raw output
- surface uncertainty explicitly when the oracle is weak or incomplete
- prefer a small number of strong, well-evidenced judgments over broad but shallow coverage

## Objective

Determine whether Drift reports the right architectural problems, avoids false positives, and remains internally consistent across analysis modes.

## Success Criteria

The task is complete only if you can answer all of the following with evidence:
- Which signals produced true positives, false positives, and false negatives
- Whether `scan` and `analyze` tell a materially consistent story
- Whether any signal is too noisy or too weak for agent-driven repair workflows
- Which signal-quality improvements should be prioritized next

## Operating Rules

- Be evidence-first. For each quality claim, cite the triggering file, code pattern, and Drift output.
- Prefer repository-realistic cases. Use synthetic fixtures only when the repo does not expose a clean oracle for a given signal.
- Separate observed behavior from judgment.
- If signal quality is unclear, say what additional oracle or benchmark would be required.
- Treat signal trustworthiness as more important than output volume.

## Evaluation Labels

Use these labels consistently for every signal you assess:

- `trusted`: behavior matches the oracle closely enough for agent use
- `needs_review`: partly useful, but precision or recall is not good enough to trust blindly
- `unsafe`: currently too misleading for autonomous decisions

## Required Artifacts

Create artifacts under `work_artifacts/drift_signal_quality_<DATE>/`:

1. `signal_inventory.md`
2. `scan_results.json`
3. `analyze_results.json`
4. `oracle_cases.md`
5. `signal_quality_report.md`

## Workflow

### Phase 0: Establish the signal inventory

Inventory the currently available signals from real CLI output and record their abbreviations, names, and any available descriptions.

At minimum, verify:
- which signals are exposed directly to users
- which commands can be used as evidence sources for signal behavior
- whether signal-level filtering is available

### Phase 1: Build an oracle set

Create or identify a small but explicit oracle for each signal you test.

Use one of these oracle sources:
- an existing repository location with a clearly explainable architectural issue
- a focused sandbox fixture with one known violation pattern
- a previously documented benchmark or validation artifact in the repo

For each oracle case, record:
- expected signal
- expected severity or ranking behavior if relevant
- why this should be considered a positive case
- what a false positive would look like nearby

### Phase 2: Measure repository results

Run both user-facing and deeper analysis commands where relevant, such as:

```bash
drift scan --max-findings 25 --response-detail detailed
drift analyze --repo . --output-format json
```

If signal filtering is available, test focused runs for selected signals.

For each tested signal, capture:
- true positives
- false positives
- false negatives
- ambiguous cases that require maintainer judgment

### Phase 3: Cross-validate outputs

Compare `scan` and `analyze` for the same repository state.

Check whether:
- the same major problems appear in both views
- the dominant signals are ranked consistently enough to guide action
- the machine-readable output preserves the same meaning as the human-facing summary

Document mismatches explicitly.

### Phase 4: Judge actionability

For each tested signal, answer:
- Can an agent trust this signal enough to start a fix plan?
- Does the output identify a clear cause or only a vague symptom?
- Would an autonomous change based on this signal be safe, risky, or blocked?

### Phase 5: Produce the report

Use this report structure:

```markdown
# Drift Signal Quality Report

**Date:** [DATE]
**drift-Version:** [VERSION]
**Repository:** [REPO NAME]

## Summary Table

| Signal | Oracle coverage | TP | FP | FN | Verdict | Notes |
|--------|------------------|----|----|----|---------|-------|

## Cross-Validation

| Comparison | Consistent? | Evidence | Impact |
|------------|-------------|----------|--------|

## Trusted Signals

[List]

## Signals Needing Review

[List]

## Unsafe Signals

[List]

## Priority Improvements

1. [...]
2. [...]
3. [...]
```

## Decision Rule

If the signal output is not trustworthy enough for an autonomous next step, say so plainly. Do not hide uncertainty behind a generic summary.

## GitHub Issue Creation

At the end of the workflow, create GitHub issues in `sauremilk/drift` for every reproducible signal-quality problem that is important enough to act on.

### Create issues for

- signals rated `unsafe`
- repeated or high-impact `needs_review` cases
- cross-validation mismatches between `scan` and `analyze`
- missing explanations, filtering, or output structure that prevents reliable signal evaluation

### Do not create issues for

- one-off local environment noise
- cases where the oracle itself is weak and the product problem is not yet reproducible
- duplicate problems already covered by an existing issue

### Required issue rules

- search for an existing issue first
- create at most one issue per concrete problem
- reference the exact signal, command, and evidence file
- state whether the problem is primarily precision, recall, ranking, or explanation quality
- use the label `agent-ux` plus any more specific label if appropriate

### Issue title format

`[signal-quality] <concise problem summary>`

### Issue body template

```markdown
## Observed behavior

[What Drift reported, and why it appears wrong or incomplete]

## Expected behavior

[What the signal should have reported instead]

## Reproduction

drift-Version: [VERSION]
Signal: [SIGNAL]
Command: `drift ...`
Evidence: [ARTIFACT PATH]

## Impact

- [ ] Precision problem
- [ ] Recall problem
- [ ] Ranking problem
- [ ] Explanation problem

## Source

Automatically created from `.github/prompts/drift-signal-quality.prompt.md` on [DATE].
```

### Completion output

End with:

```text
Created issues:
- #[NUMBER]: [TITLE] - [URL]

Skipped issues already covered:
- [TITLE] -> #[NUMBER]
```