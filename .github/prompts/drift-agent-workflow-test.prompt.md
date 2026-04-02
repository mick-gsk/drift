---
name: "Drift Agent Workflow Test"
agent: agent
description: "End-to-end drift CLI workflow test optimized for Claude Opus 4.6: inventory every command, exercise real maintainer workflows, rate agent UX, and file GitHub issues for reproducible problems."
---

# Drift Agent Workflow Test

You are Claude Opus 4.6 acting as a coding agent that must test `drift-analyzer` in a real maintainer workflow, not a toy demo. Complete the workflow end to end. After every meaningful step, explicitly judge the command response from an agent perspective as `sufficient`, `insufficient`, or `misleading`.

## Objective

Test **all currently available CLI capabilities** of `drift-analyzer` in realistic repository workflows and produce a final report that answers:
- Which commands worked well in practice
- Which commands produced unclear, incomplete, or low-value results
- Where an autonomous agent reached a dead end
- Which commands are usable for real maintainer, CI, refactoring, onboarding, and AI-integration workflows
- Which improvements should be prioritized next

## Claude Execution Mode

Use these operating rules throughout the workflow:
- Be evidence-first. Separate what the CLI actually returned from your interpretation of it.
- Be explicit about uncertainty. If you have to infer intent, say so.
- Keep a live coverage matrix from Phase 0 onward. Do not reconstruct it from memory at the end.
- Prefer real repository scenarios over synthetic examples. Only use artificial changes when a command strictly requires a diff, empty repo, or isolated write target.
- When output is long, save the raw output to an evidence file and summarize only the decision-relevant parts in the report.
- Treat agent UX as the main evaluation target: can an autonomous coding agent continue confidently after this response?
- Compare competing next-step interpretations before deciding that a command is sufficient or misleading.
- Prefer structured verdict tables over loose prose once enough evidence is available.

## Rating Rubric

Use these labels consistently:

- `sufficient`: the response gives enough trustworthy detail for the next step without guessing
- `insufficient`: partially useful, but missing key data, prioritization, filtering, or decision support
- `misleading`: likely to push the agent toward a wrong action or false confidence

Use these execution statuses consistently:

- `tested`
- `justified_skip`
- `blocked`

## Required Outputs

Create and maintain these artifacts:

1. Evidence directory: `work_artifacts/drift_agent_test_<DATE>/`
2. Sandbox directory for write-heavy tests: `work_artifacts/drift_agent_test_<DATE>/sandbox/`
3. Final report: `work_artifacts/drift_agent_test_<DATE>.md`
4. Coverage matrix covering every discovered command and relevant subcommand

Recommended evidence naming pattern:

- `phase00_help.txt`
- `phase01_scan_concise.txt`
- `phase03_fix_plan_signal.json`
- `phase08_invalid_signal_error.json`

For every executed command, capture at minimum:

- exact command
- exit status if available
- raw output evidence file or `n/a`
- short agent-UX verdict
- next-step implication

## Ground Rules

- Use shell- and platform-appropriate commands. If examples are written in POSIX syntax, translate them to PowerShell or the current environment when needed.
- Discover the CLI surface **dynamically** via `drift --help` and `drift <command> --help`. Never assume the command list is static.
- Every discovered top-level command must appear in the final report with one status: `tested`, `justified_skip`, or `blocked`.
- For grouped commands such as `baseline` and `config`, inventory and test the relevant subcommands as well.
- Prefer write operations inside the sandbox unless the command only makes sense against the real repository.
- If a command cannot be fully exercised in this environment, still perform the most realistic partial test and document the exact boundary.
- If a command has materially different human-oriented and machine-oriented output modes, test at least one of each and explicitly note what was not tested.
- Save relevant raw outputs, JSON artifacts, SARIF files, generated prompts, and badge outputs under `work_artifacts/drift_agent_test_<DATE>/`.
- For error handling, test machine-readable failures where meaningful, for example with `DRIFT_ERROR_FORMAT=json`.
- Do not file GitHub issues for purely local environment noise unless the CLI error handling itself is the product problem.

## Mandatory Coverage

The live inventory from `drift --help` is authoritative. As long as these commands exist, they must appear in a meaningful workflow at least once:

- `scan`
- `analyze`
- `explain`
- `fix-plan`
- `diff`
- `validate`
- `check`
- `baseline save`
- `baseline diff`
- `config validate`
- `config show`
- `init`
- `copilot-context`
- `export-context`
- `mcp`
- `patterns`
- `timeline`
- `trend`
- `self`
- `badge`

If `drift --help` reveals additional commands, extend coverage automatically and test them too.

---

## Phase 0: Setup and CLI Inventory

**This phase is mandatory and may not be skipped.**

Install the latest `drift-analyzer` from PyPI and verify installation:

```bash
pip install --upgrade drift-analyzer
drift scan --help
```

Check the installed version:

```bash
python -c "import drift; print(drift.__version__)"
```

Compare it with the newest version on PyPI:

```bash
pip index versions drift-analyzer 2>/dev/null || pip install drift-analyzer== 2>&1 | grep -oP 'from versions: \K.*'
```

Then inventory the real CLI surface:

```bash
drift --help
drift baseline --help
drift config --help
```

Immediately create a **coverage matrix** with these columns and keep it updated for the rest of the workflow:

| Command | Category | Planned real-world use case | Status | Evidence file |
|---------|----------|-----------------------------|--------|---------------|

### Evaluate
- [ ] The installed version matches the newest version available on PyPI
- [ ] `drift scan --help` exposes the expected parameters, including `--max-findings` and `--response-detail`
- [ ] `drift --help` was inventoried and the coverage matrix was created immediately
- [ ] `baseline` and `config` subcommands were inventoried separately
- [ ] If the installed version is not the newest, the gap was documented and testing continued with the available version

Record the installed version exactly. Use it later in the final report under `drift-Version`.

---

## Phase 1: Agent Session Triage on the Real Repository

Use the current repository the way a coding agent would at the beginning of a real session.

Run at minimum:

```bash
drift scan --max-findings 15 --response-detail concise
drift scan --max-findings 15 --response-detail detailed
```

Then rerun the scan in at least one realistic scope derived from the first scan:

```bash
drift scan --target-path <HIGH_VALUE_FOLDER> --max-findings 10 --response-detail concise
```

### Evaluate
- [ ] Are `recommended_next_actions` clear enough to determine the next step?
- [ ] Is `accept_change` unambiguous?
- [ ] Is there a clear entry point such as `fix_first` or an obviously highest-priority finding?
- [ ] If findings exceed 20, is a baseline workflow recommended?
- [ ] Do `concise` and `detailed` differ in a way that is materially useful for an agent?
- [ ] Can a concrete repair or review workflow be derived from the scan?

---

## Phase 2: Explain - Test Signal Understanding

Take the highest-scoring signal from Phase 1 and run:

```bash
drift explain <SIGNAL_ABBREVIATION>
```

If the scan surfaced multiple clearly different problem classes, explain at least **two** signals: the dominant one and a second one with a different cause pattern.

### Evaluate
- [ ] Does the explanation tell an agent how to react?
- [ ] Is it clear which code patterns trigger the signal?
- [ ] Are there actionable hints rather than only theory?
- [ ] Is it clear how the signal translates into a real refactoring or review step?

---

## Phase 3: Fix Plan and Real Repair Preparation

### 3a: Unscoped plan for the whole repository

```bash
drift fix-plan --max-tasks 5
```

### 3b: Scoped to one folder

Choose the folder with the most relevant findings from Phase 1:

```bash
drift fix-plan --max-tasks 5 --target-path <FOLDER>
```

### 3c: Scoped to one signal

```bash
drift fix-plan --signal <SIGNAL> --max-tasks 3
```

### 3d: Concrete task for real execution

Choose the most implementable task from the results above and attempt to prepare **one real, small, low-risk improvement** in the repository. If useful, tighten the plan further with:

```bash
drift fix-plan --finding-id <FINDING_ID>
```

If no safe real improvement is possible, document why and name the smallest realistic next step instead of jumping straight to an artificial change.

### Evaluate each variant
- [ ] Are the tasks concrete enough to execute directly?
- [ ] Do they include file paths and line numbers?
- [ ] Is there `success_criteria` for each task?
- [ ] Is `automation_fitness` present for each task?
- [ ] Does `--target-path` filter correctly with no tasks outside scope?
- [ ] Does `--finding-id` help transition from planning to real implementation?
- [ ] Is it obvious which task an autonomous coding agent should attempt first?

---

## Phase 4: Real Change Review Loop

If you made a real small change in Phase 3, inspect the working tree the way an agent or reviewer would before a commit.

Run at minimum:

```bash
drift diff --uncommitted --response-detail detailed
```

If you intentionally prepared staged changes, also test:

```bash
drift diff --staged-only --response-detail concise
```

If no real change was possible, create a minimal test change **only as a fallback** and explicitly document why the realistic path was not possible.

### Evaluate
- [ ] Is `accept_change` justified clearly?
- [ ] Are `in_scope_accept` and `out_of_scope_noise` distinguished?
- [ ] If `accept_change=false` is caused only by out-of-scope noise, is that stated explicitly?
- [ ] Are `recommended_next_actions` operationally useful?
- [ ] Is there any dead end where the agent cannot continue?
- [ ] Does the diff output support a real pre-commit or PR review workflow?

---

## Phase 5: Validate, Check, and CI Relevance

### 5a: Confirm the result

```bash
drift validate
```

If a baseline or generated file artifacts exist from earlier phases, also test a realistic comparison path:

```bash
drift validate --baseline <BASELINE_FILE>
```

### 5b: Test CI and gate usage

Run the command the way it would be used in CI or a pre-push gate:

```bash
drift check --fail-on none --json --compact
drift check --fail-on high --output-format rich
```

If a baseline exists, also test its effect:

```bash
drift check --fail-on none --baseline <BASELINE_FILE> --json --compact
```

### Evaluate
- [ ] Does the response confirm progress relative to Phase 1?
- [ ] Is it clear whether the changes improved the drift score?
- [ ] Is `check` directly usable for CI, pre-push, or PR gates?
- [ ] Are exit behavior, output format, and `fail-on` semantics clear from an agent perspective?

---

## Phase 6: Full Analysis, Baseline, and Repository Intelligence

This phase tests the commands maintainers would use for deeper architecture work.

### 6a: Full analysis

```bash
drift analyze --repo . --output-format rich
drift analyze --repo . --output-format json -o work_artifacts/drift_agent_test_<DATE>/analyze.json
drift analyze --repo . --output-format sarif -o work_artifacts/drift_agent_test_<DATE>/analyze.sarif
```

### 6b: Baseline for incremental adoption

```bash
drift baseline save --repo . --output work_artifacts/drift_agent_test_<DATE>/.drift-baseline.json
drift baseline diff --repo . --baseline-file work_artifacts/drift_agent_test_<DATE>/.drift-baseline.json --format json
```

### 6c: Repository intelligence and reporting

Then test the remaining analysis and reporting commands in appropriate real cases:

```bash
drift patterns
drift timeline
drift trend
drift self --format json
drift badge --output work_artifacts/drift_agent_test_<DATE>/badge.txt
```

### Evaluate
- [ ] Is `analyze` informative enough for a maintainer to derive priorities?
- [ ] Is `baseline save/diff` genuinely useful for incremental adoption or noise reduction?
- [ ] Do `patterns`, `timeline`, and `trend` help real architecture decisions, or do they mostly add surface area?
- [ ] Is `self` useful for dogfooding, regression detection, or demos?
- [ ] Does `badge` generate a meaningful output for README or CI artifacts?

---

## Phase 7: Setup, Config, and AI Integration Workflows

This phase tests real onboarding and agent-integration paths.

### 7a: Prepare a sandbox

Create an isolated test repository or test directory under `work_artifacts/drift_agent_test_<DATE>/sandbox/`. Use it for write-heavy integration commands.

### 7b: Init and config

Test the onboarding workflow in the sandbox:

```bash
drift init --full --repo <SANDBOX_REPO>
drift config validate --repo <SANDBOX_REPO>
drift config show --repo <SANDBOX_REPO>
```

### 7c: Copilot and prompt context

Test both preview and file-output paths:

```bash
drift copilot-context --repo .
drift copilot-context --repo . --write -o work_artifacts/drift_agent_test_<DATE>/copilot-instructions.md

drift export-context --repo . --format instructions --write -o work_artifacts/drift_agent_test_<DATE>/negative-context.instructions.md
drift export-context --repo . --format prompt --write -o work_artifacts/drift_agent_test_<DATE>/negative-context.prompt.md
drift export-context --repo . --format raw --write -o work_artifacts/drift_agent_test_<DATE>/negative-context.raw.md
```

### 7d: MCP integration

Test at least these two paths:

```bash
drift mcp
drift mcp --serve
```

If `drift mcp --serve` starts successfully and blocks, run it with a timeout or as a short-lived background process and evaluate startup behavior, prerequisites, and usability. If optional dependencies are missing, evaluate whether the error is agent-usable.

### Evaluate
- [ ] Is `init` immediately usable for a new repository?
- [ ] Are `config validate` and `config show` sufficient for troubleshooting and team onboarding?
- [ ] Are `copilot-context` and `export-context` usable in real AI workflows?
- [ ] Is the MCP path documented and testable clearly enough for an agent?

---

## Phase 8: Edge Cases and Machine-Readable Errors

### 8a: Invalid signal

```bash
drift fix-plan --signal INVALID_SIGNAL
```

- [ ] Is there a helpful error message with valid values?

### 8b: Empty target path

```bash
drift fix-plan --target-path nonexistent/path
```

- [ ] Is it communicated clearly that no tasks were found?

### 8c: Scan with signal filter

```bash
drift scan --signals PFS,AVS --max-findings 5
```

- [ ] Are only the requested signals shown?

### 8d: Missing baseline

```bash
drift baseline diff --repo <SANDBOX_REPO>
```

- [ ] Is the error message clear and does it lead to the next sensible step?

### 8e: Did-you-mean for wrong option names

```bash
drift scan --max-fidings 5
```

- [ ] Is there a useful correction hint?

### 8f: Machine-readable error path

```bash
DRIFT_ERROR_FORMAT=json drift fix-plan --signal INVALID_SIGNAL
```

- [ ] Is the error format stable, complete, and directly automatable for agent workflows?

---

## Phase 9: Final Report

Create a structured report in this format:

```markdown
# Drift Agent Workflow Test Result

**Date:** [DATE]
**drift-Version:** [VERSION from the installed CLI]
**Repository:** [REPO NAME]

## Summary

| Phase | Command | Result | Agent suitability |
|-------|---------|--------|-------------------|
| 1     | scan | ✅/⚠️/❌ | [short judgment] |
| 2     | explain | ✅/⚠️/❌ | [short judgment] |
| 3a    | fix-plan | ✅/⚠️/❌ | [short judgment] |
| 3b    | fix-plan --target-path | ✅/⚠️/❌ | [short judgment] |
| 3c    | fix-plan --signal | ✅/⚠️/❌ | [short judgment] |
| 3d    | fix-plan --finding-id | ✅/⚠️/❌ | [short judgment] |
| 4     | diff | ✅/⚠️/❌ | [short judgment] |
| 5a    | validate | ✅/⚠️/❌ | [short judgment] |
| 5b    | check | ✅/⚠️/❌ | [short judgment] |
| 6a    | analyze | ✅/⚠️/❌ | [short judgment] |
| 6b    | baseline save/diff | ✅/⚠️/❌ | [short judgment] |
| 6c    | patterns/timeline/trend/self/badge | ✅/⚠️/❌ | [short judgment] |
| 7b    | init + config | ✅/⚠️/❌ | [short judgment] |
| 7c    | copilot-context + export-context | ✅/⚠️/❌ | [short judgment] |
| 7d    | mcp | ✅/⚠️/❌ | [short judgment] |
| 8a    | invalid signal | ✅/⚠️/❌ | [short judgment] |
| 8b    | empty result | ✅/⚠️/❌ | [short judgment] |
| 8c    | signal filter | ✅/⚠️/❌ | [short judgment] |
| 8d    | missing baseline | ✅/⚠️/❌ | [short judgment] |
| 8e    | did-you-mean | ✅/⚠️/❌ | [short judgment] |
| 8f    | machine-readable errors | ✅/⚠️/❌ | [short judgment] |

## Coverage Matrix

| Command | Test case | Status | Agent rating | Evidence |
|---------|-----------|--------|--------------|----------|
| [every inventoried command and subcommand] | [...] | tested / justified_skip / blocked | sufficient / insufficient / misleading | [path or n/a] |

## Practical Workflows

### 1. Coding agent session start
[Which commands were genuinely useful here?]

### 2. Real repair or refactoring preparation
[Which commands directly helped with implementation planning?]

### 3. PR or CI gate
[Which commands are usable for review, pre-commit, or CI?]

### 4. Team onboarding or first-time adoption
[How usable are init, baseline, and config?]

### 5. AI integration
[How usable are copilot-context, export-context, and mcp?]

## Dead Ends

[List every point where the workflow could not continue cleanly]

## Ambiguous Answers

[List every point where the agent had to guess]

## Prioritized Improvements

1. [Highest priority - blocks agent workflow]
2. [...]
3. [...]
```

Save the report as `work_artifacts/drift_agent_test_<DATE>.md`.

When reporting findings, separate:

- `Observed behavior`
- `Why this matters for an agent`
- `Recommended product improvement`

---

## Phase 10: Create GitHub Issues for Drift

**This is the main purpose of the workflow.** Convert the problems identified in the report into issues in the drift repository at [sauremilk/drift](https://github.com/sauremilk/drift).

### Rules for issue creation

- Create issues **only** for problems rated ⚠️ or ❌ in the summary
- Create **no issue** for ✅ outcomes
- Create at most one issue per concrete problem; avoid duplicates
- Search the repository first to see whether a similar issue already exists
- Always reference the practical workflow where the problem occurred
- Always mention the exact command and, when available, the evidence file under `work_artifacts/`
- Only file issues for reproducible product defects, missing guidance, or agent-UX gaps supported by evidence

### Issue format

For each problem from `Dead Ends` and `Ambiguous Answers`, create an issue with:

**Title:** `[agent-ux] <one-sentence problem summary>`

**Body template:**

```markdown
## Observed behavior

[What did the agent actually receive?]

## Expected behavior

[What would the agent have needed in order to continue confidently?]

## Reproduction

drift-Version: [VERSION]
Command: `drift <command> [parameters]`
Repo: [REPO NAME]

## Impact

- [ ] Dead end (agent cannot continue)
- [ ] Misinterpretation risk (agent must guess)
- [ ] Information loss (relevant data is missing from the response)

## Source

Automatically created from `.github/prompts/drift-agent-workflow-test.prompt.md` on [DATE].
```

**Labels:** `agent-ux`

### Priority rule

Create issues in this order:

1. Dead ends first
2. Ambiguous answers second
3. Missing information third

### Completion output

At the end, print a list of all created issues:

```text
Created issues:
- #[NUMBER]: [TITLE] - [URL]
- ...

Skipped problems (already covered by an existing issue):
- [TITLE] -> #[NUMBER]
```

## Success Criteria

The workflow is complete only if:

- the coverage matrix includes **all currently available commands** from `drift --help`, plus relevant subcommands
- at least four real usage scenarios were exercised: session start, repair/refactoring, CI/gate, onboarding/adoption, and AI integration
- write-oriented commands produced real artifacts in `work_artifacts/` or the sandbox
- the distinction between helpful, unclear, and misleading responses is evidence-backed
- every issue-worthy problem is documented as either a newly created issue or an already existing issue

