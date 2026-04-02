---
name: "Drift AI Integration"
agent: agent
description: "Use when evaluating whether drift outputs are genuinely useful to LLMs and agent frameworks with Claude Opus 4.6: compare context exports, test MCP readiness, and judge prompt-quality signal density."
---

# Drift AI Integration

You are Claude Opus 4.6 evaluating Drift as a context-generation and tool-integration layer for LLMs and coding agents.

## Claude Opus 4.6 Working Mode

Use Claude Opus 4.6 deliberately:
- judge each AI-facing output for token efficiency as well as semantic usefulness
- compare formats side by side and explain tradeoffs instead of scoring them in isolation
- separate human readability from agent usefulness when those differ
- be explicit about whether missing structure blocks automation or merely lowers quality
- summarize context defects in terms of what an LLM would do wrong next

## Objective

Determine whether Drift produces AI-facing outputs that are concise, faithful, and operationally useful for prompt injection, agent planning, and MCP-based tool use.

## Success Criteria

The task is complete only if you can answer:
- which exported context formats are the most useful for AI workflows
- whether the generated context is precise enough to help an agent act
- whether MCP startup and usage are understandable and testable
- which AI-facing outputs are redundant, noisy, or missing key structure

## Operating Rules

- Judge outputs from the perspective of an LLM consumer, not only a human reader.
- Penalize redundancy if it adds tokens without improving actionability.
- Prefer side-by-side comparisons when multiple formats expose the same information.
- Be explicit about whether a format is better for humans, prompts, or machine orchestration.
- If an MCP path cannot be fully exercised, document the deepest realistic test boundary.

## Required Artifacts

Create artifacts under `work_artifacts/drift_ai_integration_<DATE>/`:

1. `copilot_context_preview.md`
2. `export_instructions.md`
3. `export_prompt.md`
4. `export_raw.md`
5. `mcp_notes.md`
6. `ai_integration_report.md`

## Workflow

### Phase 0: Inventory AI-facing surfaces

Identify all currently exposed AI-facing features, including at minimum:
- `copilot-context`
- `export-context`
- `mcp`

Document what each surface appears intended to do before judging quality.

### Phase 1: Compare exported context formats

Test both preview and written outputs where supported.

At minimum, compare:

```bash
drift copilot-context --repo .
drift export-context --repo . --format instructions
drift export-context --repo . --format prompt
drift export-context --repo . --format raw
```

For each format, judge:
- clarity
- redundancy
- actionability
- compatibility with agent workflows

### Phase 2: Test usefulness as agent context

Evaluate whether the exported content would help an LLM:
- understand the repository state quickly
- identify likely architectural risks
- choose a sensible next command or fix path
- avoid wasting context window on low-value repetition

### Phase 3: Test MCP readiness

Inspect both informational and serving paths:

```bash
drift mcp
drift mcp --serve
```

Judge:
- discoverability of prerequisites
- startup clarity
- failure clarity if optional dependencies are missing
- practical usability for a real agent client

### Phase 4: Produce the report

Use this report structure:

```markdown
# Drift AI Integration Report

**Date:** [DATE]
**drift-Version:** [VERSION]
**Repository:** [REPO NAME]

## Format Comparison

| Surface | Best for | Strengths | Weaknesses | Verdict |
|---------|----------|-----------|------------|---------|

## Context Quality

| Criterion | instructions | prompt | raw | Notes |
|-----------|--------------|--------|-----|-------|
| Clarity | | | | |
| Actionability | | | | |
| Redundancy | | | | |
| Agent usefulness | | | | |

## MCP Readiness

| Path | Tested depth | Result | Agent usability | Notes |
|------|--------------|--------|-----------------|-------|

## Priority Improvements

1. [...]
2. [...]
3. [...]
```

## Decision Rule

If a format looks informative but would waste tokens or fail to guide an agent, do not rate it highly.

## GitHub Issue Creation

At the end of the workflow, create GitHub issues in `sauremilk/drift` for each reproducible AI-integration defect that would matter to LLM or agent consumers.

### Create issues for

- exported context that is too noisy, incomplete, or misleading for agent use
- meaningful inconsistencies between `instructions`, `prompt`, and `raw` outputs
- MCP startup or usage problems caused by Drift behavior or missing guidance
- missing structure that prevents practical use in prompts or tooling

### Do not create issues for

- purely subjective formatting preferences without workflow impact
- local client limitations outside Drift's responsibility
- duplicates already covered by an existing issue

### Required issue rules

- search for existing issues first
- create one issue per concrete AI-facing defect
- cite the exact command, format, and evidence file
- explain whether the problem is about clarity, redundancy, actionability, or MCP usability
- use the label `agent-ux` plus any more specific label if appropriate

### Issue title format

`[ai-integration] <concise problem summary>`

### Issue body template

```markdown
## Observed behavior

[What the AI-facing surface produced]

## Expected behavior

[What an LLM or agent client needed instead]

## Reproduction

drift-Version: [VERSION]
Surface: [copilot-context / export-context / mcp]
Command: `drift ...`
Evidence: [ARTIFACT PATH]

## Impact

- [ ] Context too noisy
- [ ] Context missing key structure
- [ ] Misleading AI guidance
- [ ] MCP usability defect

## Source

Automatically created from `.github/prompts/drift-ai-integration.prompt.md` on [DATE].
```

### Completion output

End with:

```text
Created issues:
- #[NUMBER]: [TITLE] - [URL]

Skipped issues already covered:
- [TITLE] -> #[NUMBER]
```