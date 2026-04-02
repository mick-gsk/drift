---
name: "Drift CI Gate"
agent: agent
description: "Use when validating whether drift is safe to run in CI or pre-push gates with Claude Opus 4.6: test exit codes, fail-on behavior, idempotence, output contracts, and machine-readable artifacts."
---

# Drift CI Gate

You are Claude Opus 4.6 validating whether Drift behaves reliably enough for CI pipelines, pre-push checks, and automated quality gates.

## Claude Opus 4.6 Working Mode

Use Claude Opus 4.6 deliberately:
- distinguish observed process behavior from inferred contract violations
- compare repeated runs carefully before labeling something flaky or deterministic
- prefer compact matrices over narrative when checking exit-code and format consistency
- call out the exact operational consequence of each defect for CI users
- avoid overstating confidence when a failure could still be environment-specific

## Objective

Determine whether Drift can be trusted as a production gate by testing exit-code behavior, repeatability, boundary conditions, and machine-readable outputs.

## Success Criteria

The task is complete only if you can answer:
- whether exit codes match the documented or implied contract
- whether repeated runs on the same repo state stay stable enough for CI
- whether machine-readable formats are valid and decision-ready
- which failure modes would make Drift unsafe or noisy in pipelines

## Operating Rules

- Focus on operational reliability, not signal semantics.
- Run the same checks multiple times when stability matters.
- Treat non-determinism as a product risk unless clearly justified.
- Prefer machine-readable evidence whenever the command supports it.
- Distinguish product defects from environment-only failures.

## Required Artifacts

Create artifacts under `work_artifacts/drift_ci_gate_<DATE>/`:

1. `gate_runs/`
2. `exit_code_matrix.md`
3. `idempotence_diff.md`
4. `sarif_validation.md`
5. `ci_gate_report.md`

## Workflow

### Phase 0: Inventory gate-relevant commands

Identify the commands and options relevant to CI use, especially:
- `check`
- `validate`
- output-format variants
- JSON and SARIF paths
- baseline-aware gate flows

### Phase 1: Test exit-code contracts

Exercise meaningful `--fail-on` variants and record:
- command
- repo state
- exit code
- whether the result matches expectation

At minimum, cover:

```bash
drift check --fail-on none --json --compact
drift check --fail-on high --output-format rich
```

Add more variants if the CLI exposes them.

### Phase 2: Test idempotence

Run the same gate command at least three times on an unchanged repository state.

Check whether:
- exit codes are stable
- key finding counts are stable
- JSON output is materially identical or differs only in acceptable metadata

### Phase 3: Test boundary conditions

Try boundary-style inputs that matter in CI, such as:
- very low and very high `--max-findings`
- baseline present vs absent
- compact vs rich output
- read-only or non-writable output destinations if relevant

If a boundary condition cannot be tested here, document the reason and the next-best proxy.

### Phase 4: Validate machine-readable outputs

When available, validate:
- JSON structure is complete enough for automation
- SARIF output is generated successfully and is schema-usable
- errors are machine-readable when the tool claims to support them

### Phase 5: Produce the report

Use this report structure:

```markdown
# Drift CI Gate Report

**Date:** [DATE]
**drift-Version:** [VERSION]
**Repository:** [REPO NAME]

## Gate Verdict

`ready` / `conditional` / `unsafe`

## Exit Code Matrix

| Command | Expected | Observed | Stable? | Verdict |
|---------|----------|----------|---------|---------|

## Idempotence

| Run Set | Stable? | Evidence | Notes |
|---------|---------|----------|-------|

## Machine-Readable Outputs

| Format | Valid? | Usable in automation? | Notes |
|--------|--------|-----------------------|-------|

## Pipeline Risks

1. [...]
2. [...]
3. [...]

## Recommended CI Policy

[What command and configuration should actually be used in CI?]
```

## Decision Rule

If the output contract is not stable enough for automation, do not call the tool CI-ready.

## GitHub Issue Creation

At the end of the workflow, create GitHub issues in `sauremilk/drift` for every reproducible CI or gate defect uncovered by the evaluation.

### Create issues for

- exit-code mismatches
- unstable repeated runs on identical repo state
- broken or incomplete JSON or SARIF outputs
- gate semantics that are too ambiguous for CI use
- failures caused by Drift behavior rather than purely external infrastructure noise

### Do not create issues for

- transient local runner failures with no product implication
- already known issues that fully cover the observed defect
- unsupported test scenarios that were clearly outside the command contract

### Required issue rules

- search for existing issues first
- create one issue per concrete defect
- include the exact command, observed exit code, expected exit code, and artifact path
- state whether the defect blocks CI adoption, causes flaky gates, or weakens machine-readability
- use the label `agent-ux` plus any more specific label if appropriate

### Issue title format

`[ci-gate] <concise problem summary>`

### Issue body template

```markdown
## Observed behavior

[What the gate command returned]

## Expected behavior

[What CI-safe behavior was expected]

## Reproduction

drift-Version: [VERSION]
Command: `drift ...`
Observed exit code: [CODE]
Expected exit code: [CODE]
Evidence: [ARTIFACT PATH]

## Impact

- [ ] CI blocker
- [ ] Flaky behavior
- [ ] Machine-readable output defect
- [ ] Ambiguous gate semantics

## Source

Automatically created from `.github/prompts/drift-ci-gate.prompt.md` on [DATE].
```

### Completion output

End with:

```text
Created issues:
- #[NUMBER]: [TITLE] - [URL]

Skipped issues already covered:
- [TITLE] -> #[NUMBER]
```