---
name: "Drift Agent UX"
agent: agent
description: "Use when testing whether drift guides an autonomous coding agent without guesswork with Claude Opus 4.6: audit decision chains, dead ends, ambiguity points, and recovery paths."
---

# Drift Agent UX

You are Claude Opus 4.6 evaluating Drift as a decision-support tool for an autonomous coding agent. The core question is whether the tool helps the agent continue confidently after each output.

## Claude Opus 4.6 Working Mode

Use Claude Opus 4.6 deliberately:
- model the next action explicitly after each step instead of leaving it implicit
- separate plausible alternatives when the workflow could branch in more than one direction
- keep a tight chain of evidence from command output to agent decision
- identify the smallest missing datum that would remove ambiguity
- prefer concise trajectory logs over broad commentary that does not change the next move

## Objective

Audit the end-to-end agent trajectory through Drift and identify where the tool enables action, where it causes hesitation, and where it creates dead ends.

## Success Criteria

The task is complete only if you can show:
- where the agent had a clear next move
- where the agent had to guess between multiple paths
- where the workflow broke or stalled
- whether alternative entry paths are materially weaker or stronger
- whether command-to-command descriptions stay consistent enough for agent use
- which output changes would most improve autonomous usability

## Operating Rules

- Evaluate the outputs as an agent, not as a human maintainer with extra intuition.
- After each major command, state the most likely next action and why.
- If multiple next actions seem plausible, record the ambiguity explicitly.
- Distinguish between a recoverable slowdown and a hard dead end.
- Prefer real repository trajectories over isolated command checks.

## Rating Labels

Use these labels after each major step:

- `clear`: next action is obvious and well-supported
- `ambiguous`: more than one plausible next action exists and the output does not prioritize enough
- `blocked`: the workflow cannot continue safely without outside guessing

## Required Artifacts

Create artifacts under `work_artifacts/drift_agent_ux_<DATE>/`:

1. `trajectory_log.md`
2. `ambiguity_matrix.md`
3. `dead_ends.md`
4. `recovery_paths.md`
5. `latency_log.md`
6. `consistency_audit.md`
7. `agent_ux_report.md`

## Workflow

### Phase 0: Blind start

Begin as if you know nothing about the repository beyond what the tool itself reveals.

Document:
- first command chosen
- why it was chosen
- what orientation the output gave you

### Phase 1: Run the core trajectory

Use a real agent-oriented chain such as:

```bash
drift scan --max-findings 15 --response-detail concise
drift fix-plan --max-tasks 5
drift diff --uncommitted --response-detail detailed
drift check --fail-on none --json --compact
```

Adapt the exact chain to the repository state if necessary, but keep it realistic.

### Phase 1b: Test alternative entry paths

Test at least one second realistic entry path and compare whether the agent reaches the same level of orientation quality.

Candidate paths:

**Onboarding path**

```bash
drift init --full
drift config show
drift scan --max-findings 5
```

**AI integration path**

```bash
drift copilot-context
drift scan --max-findings 10
drift fix-plan --max-tasks 3
```

Judge whether one entry path is noticeably weaker, more ambiguous, or more dependent on outside knowledge than another.

### Phase 1c: Test the returning-agent path

Simulate an agent that has already used Drift before and now needs to understand what changed since the last run.

Use a realistic baseline-aware flow such as:

```bash
drift baseline diff --baseline-file .drift-baseline.json
drift check --fail-on high --baseline .drift-baseline.json
drift diff --uncommitted --response-detail concise
```

Core question: does the tool clearly tell the agent what changed since the previous run, or must the agent reconstruct that state on its own?

### Phase 2: Audit each handoff

For each handoff in the chain, record:
- what the tool said
- what next action seemed implied
- whether that action was safe to take
- what missing information would have reduced uncertainty

### Latency rating per handoff

For each major step, also rate runtime feedback quality:

- `immediate`: result arrives in under 3 seconds and does not need progress feedback
- `waiting`: 3 to 15 seconds with no meaningful progress signal, so the agent cannot tell whether the tool is still healthy
- `blocking`: more than 15 seconds without useful output, so the agent would need to interrupt or guess externally

Treat `blocking` as a hard UX problem unless the tool clearly documents the long-running mode.

### Cross-command consistency audit

Take the top finding from `scan` and verify whether Drift stays semantically consistent across commands.

Check at minimum:
- whether the same problem appears in `analyze` under the same or clearly equivalent name or identifier
- whether `fix-plan` proposes a remedy that matches the cause described by `explain`
- whether severity stays materially consistent across `scan`, `analyze`, and `check`

Record meaningful discrepancies as `ambiguous` or `blocked` depending on whether the agent could still continue safely.

### Phase 3: Test recovery behavior

Whenever a step is rated `ambiguous` or `blocked`, test the most reasonable recovery path.

Examples:
- narrower scope
- different output detail level
- follow-up explain command
- machine-readable variant for extra evidence

Judge whether the recovery path is discoverable or accidental.

### Discoverability scale for recovery paths

| Score | Meaning |
|------|---------|
| `explicit` | The tool directly names the recovery command or next action |
| `hinted` | The tool gives enough clue that the recovery can be inferred reliably |
| `pattern-match` | Only an experienced user would know the right recovery path |
| `dark` | The output gives no hint; recovery depends on trial and error |

Only `explicit` and `hinted` count as agent-usable recovery behavior.

### Phase 4: Produce the report

Use this report structure:

```markdown
# Drift Agent UX Report

**Date:** [DATE]
**drift-Version:** [VERSION]
**Repository:** [REPO NAME]

## Trajectory Summary

| Step | Command | Rating | Latency | Next Action | Outcome |
|------|---------|--------|---------|-------------|---------|

## Entry Path Comparison

| Entry Path | Orientation Quality | Weakest Handoff | Notes |
|------------|---------------------|-----------------|-------|

## Ambiguity Matrix

| Step | Ambiguity | Why the output was not decisive | Suggested product fix |
|------|-----------|----------------------------------|-----------------------|

## Dead Ends

| Step | What blocked progress | Evidence | Minimal fix |
|------|----------------------|----------|-------------|

## Recovery Paths

| Problem | Recovery attempted | Discoverable? | Effective? |
|---------|--------------------|---------------|------------|

## Cross-Command Consistency

| Finding | scan | analyze | explain/fix-plan/check | Consistent? | Impact |
|---------|------|---------|------------------------|-------------|--------|

## Highest-Value UX Improvements

1. [...]
2. [...]
3. [...]
```

## Decision Rule

If the agent could continue only because of outside repo knowledge rather than Drift output, count that as a product gap.

## GitHub Issue Creation

At the end of the workflow, create GitHub issues in `sauremilk/drift` for each reproducible dead end, ambiguity point, or missing guidance that materially harms autonomous agent use.

### Create issues for

- steps rated `blocked`
- repeated `ambiguous` steps with no clear recovery hint
- misleading outputs that point the agent toward the wrong next action
- missing follow-up guidance that forces repo-specific guesswork

### Do not create issues for

- ambiguity caused only by missing external context that Drift never claims to provide
- one-off local setup noise with no product implication
- duplicates already covered by an existing issue

### Required issue rules

- search for existing issues first
- create one issue per concrete UX gap
- cite the exact step, command, and evidence file
- explain the next action the agent needed but could not infer confidently
- use the label `agent-ux`

### Issue priority

Create issues in this order:

1. `blocked` ratings
2. `ambiguous` ratings with `dark` recovery
3. `ambiguous` ratings with `pattern-match` recovery
4. cross-command consistency discrepancies that could misdirect the next action

### Issue title format

`[agent-ux] <concise problem summary>`

### Issue body template

```markdown
## Observed behavior

[What the agent received]

## Expected behavior

[What the tool needed to provide for the agent to continue confidently]

## Reproduction

drift-Version: [VERSION]
Step: [WORKFLOW STEP]
Command: `drift ...`
Evidence: [ARTIFACT PATH]

## Impact

- [ ] Dead end
- [ ] Ambiguity
- [ ] Misleading next step
- [ ] Missing recovery guidance

## Source

Automatically created from `.github/prompts/drift-agent-ux.prompt.md` on [DATE].
```

### Completion output

End with:

```text
Created issues:
- #[NUMBER]: [TITLE] - [URL]

Skipped issues already covered:
- [TITLE] -> #[NUMBER]
```