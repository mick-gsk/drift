# Implementation Plan: Agent PR Review Loop

**Branch**: `feat/agent-pr-review-loop` | **Date**: 2026-04-30 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/004-agent-pr-review-loop/spec.md`

## Summary

Implement a polling-based PR review loop that guides an agent from task completion through self-review, GitHub Copilot Review, iterative feedback addressing, and eventual approval — without human intervention for purely technical issues. The loop is implemented as a Constitution-compliant vertical slice (`src/drift/pr_loop/`), exposed via `drift pr-loop <PR_NUMBER>`, driven by a thin `scripts/pr_review_loop.py` entry point, and orchestrated by `.github/skills/drift-pr-review-loop/SKILL.md`. Configuration lives in `drift.yaml` under `pr_loop:`. Loop state is persisted to `work_artifacts/pr-loop-<PR>.json` (gitignored).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Click, Pydantic (frozen models), Rich, `subprocess` → `gh` CLI (authenticated)
**Storage**: `work_artifacts/pr-loop-<PR>.json` (gitignored temp file)
**Testing**: pytest, no precision/recall fixtures (not a signal)
**Target Platform**: Windows + Linux (cross-platform Python + `gh` CLI)
**Project Type**: CLI feature / developer tooling library
**Performance Goals**: Polling overhead negligible; `gh` CLI calls dominate latency (acceptable)
**Constraints**: Must not merge PRs; must not push to branches other than the PR's head; `--dry-run` mode must produce zero GitHub side-effects
**Scale/Scope**: Single-repo, single-PR per invocation; max 5 rounds by default

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] **I. Library-First**: Core logic lives in `src/drift/pr_loop/`. `scripts/pr_review_loop.py` is a thin `sys.exit(main())` wrapper. No logic in the CLI entry point or the SKILL.
- [x] **II. Test-First**: Tests written before implementation: `tests/pr_loop/test_models_unit.py`, `test_engine_unit.py`, `test_gh_contract.py`, `test_cmd_integration.py`.
- [x] **III. Functional Programming**: `_models.py` uses `frozen=True` Pydantic models. `_engine.py` contains pure functions for state transitions. Side effects (gh CLI calls, file I/O) isolated in `_gh.py` and `_state.py`.
- [x] **IV. CLI Interface & Observability**: `drift pr-loop <PR_NUMBER>` Click subcommand. Both `--format rich` and `--format json` supported. Errors to stderr.
- [x] **V. Simplicity & YAGNI**: Polling over webhooks — no server, no persistent process. State in a single JSON file. No DB, no queue, no retry library. Max 5 rounds by default.
- [x] **VI. Vertical Slices**: `src/drift/pr_loop/` owns models, engine, gh side-effects, output formatting, CLI subcommand, and tests. Only shared primitives from `src/drift/config/` are imported.

## Project Structure

### Documentation (this feature)

```text
specs/004-agent-pr-review-loop/
├── plan.md              # This file
├── spec.md              # Clarified specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── contracts/
│   └── cli-pr-loop.md   # CLI contract (drift pr-loop)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
# Vertical Slice (Constitution Principle VI)
src/drift/pr_loop/
├── __init__.py           # Public API: loop_until_approved, LoopState, PrLoopConfig
├── _models.py            # Frozen Pydantic models: LoopState, ReviewRound, ReviewerVerdict,
│                         #   ReviewComment, LoopExitStatus, ReviewState
├── _state.py             # Pure I/O: load_loop_state(), save_loop_state()
├── _engine.py            # Pure logic: poll_reviews(), collect_unresolved_comments(),
│                         #   next_loop_state(), should_escalate(), should_exit()
├── _gh.py                # Side-effects only: post_self_review(), request_reviewers(),
│                         #   push_fix_commits(), post_escalation_summary()
│                         #   (all calls via subprocess → gh CLI)
├── _output.py            # Rich + JSON output rendering
└── _cmd.py               # Click subcommand: @drift_cli.command("pr-loop")

# Config extension (existing file)
src/drift/config/_loader.py   # Add PrLoopConfig model + pr_loop field on DriftConfig

# Script entry point (thin wrapper)
scripts/pr_review_loop.py     # sys.exit(main()) wrapper around drift.pr_loop CLI

# Copilot orchestration skill (agent primitive)
.github/skills/drift-pr-review-loop/
└── SKILL.md              # When/how the agent invokes drift pr-loop and interprets output

# Tests
tests/pr_loop/
├── __init__.py
├── test_models_unit.py        # Pydantic model validation, state transitions
├── test_engine_unit.py        # Pure function tests: polling logic, exit conditions
├── test_state_unit.py         # load/save round-trip, corrupted-file handling
├── test_gh_contract.py        # Contract tests: gh CLI call shapes (subprocess mock)
└── test_cmd_integration.py    # Click CLI integration: exit codes, output formats

# Schema (updated as part of DriftConfig change)
drift.schema.json             # Regenerated after PrLoopConfig added to DriftConfig
```

**Structure Decision**: Vertical slice `src/drift/pr_loop/`. Justification: this feature owns its own models, state machine, side-effect layer, and CLI subcommand — it does not share logic with existing slices. The only external import is `DriftConfig` from `src/drift/config/`.

## Complexity Tracking

No Constitution violations. No justified exceptions required.

---

## Implementation Phases

### Phase A — Foundation (TDD Red): Failing Tests + Models

**Goal**: All test files exist with meaningful failing tests before any implementation is written.

| Task | File | Notes |
|------|------|-------|
| A1 | `tests/pr_loop/test_models_unit.py` | Test `PrLoopConfig` validation rules (min rounds, min interval, non-empty reviewers); test `LoopState` transitions; test `ReviewState` enum completeness |
| A2 | `tests/pr_loop/test_engine_unit.py` | Test `should_escalate()`, `should_exit()`, `next_loop_state()` with synthetic verdict lists; test timeout logic; test contradiction detection |
| A3 | `tests/pr_loop/test_state_unit.py` | Test `load_loop_state` / `save_loop_state` round-trip; test corrupted JSON handling; test missing file returns fresh state |
| A4 | `tests/pr_loop/test_gh_contract.py` | Contract tests for `post_self_review()`, `request_reviewers()`, `post_escalation_summary()` — assert correct `gh` CLI call shapes via `subprocess` mock |
| A5 | `tests/pr_loop/test_cmd_integration.py` | CLI exit codes (0/1/2/3), `--dry-run` produces no writes, `--format json` output schema matches contract |
| A6 | `src/drift/config/_loader.py` | Add `PrLoopConfig` Pydantic model; add `pr_loop: PrLoopConfig \| None = None` field to `DriftConfig` |
| A7 | Regenerate `drift.schema.json` | Run schema regen after A6 to prevent `test_config_schema.py` CI failure |

**Exit gate**: `pytest tests/pr_loop/ -x` shows all tests collected and failing (not erroring). `make check` passes for non-pr-loop tests.

---

### Phase B — Implementation (TDD Green): Library Core

**Goal**: All Phase A tests pass. No new logic outside `src/drift/pr_loop/`.

| Task | File | Notes |
|------|------|-------|
| B1 | `src/drift/pr_loop/_models.py` | Implement frozen Pydantic models per data-model.md |
| B2 | `src/drift/pr_loop/_state.py` | Implement `load_loop_state` / `save_loop_state` using `pathlib.Path.write_text(encoding="utf-8")` |
| B3 | `src/drift/pr_loop/_engine.py` | Implement pure state-transition functions; polling loop logic (calls `_gh.get_reviews()` then checks exit conditions) |
| B4 | `src/drift/pr_loop/_gh.py` | Implement `gh` CLI wrappers via `subprocess.run(check=True, capture_output=True, text=True)`; parse JSON output |
| B5 | `src/drift/pr_loop/_output.py` | Implement Rich + JSON rendering; use `console.print(markup=False)` for literal bracket text |
| B6 | `src/drift/pr_loop/_cmd.py` | Implement Click subcommand; wire precondition checks; handle all 4 exit codes |
| B7 | `src/drift/pr_loop/__init__.py` | Export public API: `loop_until_approved`, `LoopState`, `PrLoopConfig` |
| B8 | Register CLI subcommand | Add `from drift.pr_loop._cmd import pr_loop_cmd` to `src/drift/cli.py` (or equivalent registration point) |
| B9 | `scripts/pr_review_loop.py` | Thin wrapper: `from drift.pr_loop._cmd import main; sys.exit(main())` |

**Exit gate**: `pytest tests/pr_loop/ -x` all green. `make check` passes. `drift pr-loop --help` outputs correct usage.

---

### Phase C — Orchestration Skill

**Goal**: The Copilot agent has a clear, hardened SKILL it can invoke instead of guessing the workflow.

| Task | File | Notes |
|------|------|-------|
| C1 | `.github/skills/drift-pr-review-loop/SKILL.md` | Write SKILL per prompt-engineering rules: discovery-taugliches Frontmatter; describe preconditions, tool calls (`drift pr-loop`), output interpretation, and escalation handling; no duplication of spec prose |

**SKILL structure**:
- **Trigger**: agent has just opened or updated a PR and wants to drive it to approval
- **Preconditions**: local gates passed, `gh auth status` OK, PR number known
- **Step 1**: run `drift pr-loop <PR_NUMBER> --format json`
- **Step 2**: interpret exit code (0=done, 1=escalated → post human-readable summary, 2/3=error → diagnose)
- **Step 3**: if `status == ESCALATED`, read `work_artifacts/pr-loop-<PR>.json` for unresolved items and surface them to the human
- **Stop condition**: exit code 0 or human escalation acknowledged

---

### Phase D — Hardening & Documentation

**Goal**: No regressions, schema in sync, quickstart written.

| Task | File | Notes |
|------|------|-------|
| D1 | `specs/004-agent-pr-review-loop/quickstart.md` | Minimal "how to use" for the agent: install check, `drift.yaml` snippet, one-liner invocation |
| D2 | `CHANGELOG.md` | `feat:` entry via `make changelog-entry` — do not hand-format |
| D3 | `drift.yaml` | Add `pr_loop:` section with defaults (document but do not activate in strict mode) |
| D4 | `make check` | Full local CI must pass clean |
| D5 | `pre-commit run --all-files` | Secrets, typos, shellcheck, EOF — all green |
| D6 | `make gate-check COMMIT_TYPE=feat` | Evidence artifact required — create `benchmark_results/v<VERSION>_agent-pr-review-loop_feature_evidence.json` via `drift-evidence-artifact-authoring` skill |

---

## Risk Register (this feature)

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| `github-copilot[bot]` not enabled at repo level → bot never reviews | Medium | `_engine.py` treats `NO_RESPONSE` after timeout as soft failure; escalation summary explicitly states bot was not seen |
| `gh` CLI not authenticated in CI | Low | Precondition check (exit code 3) catches this before any loop starts |
| `drift.schema.json` not regenerated after `DriftConfig` change | High | Task A7 is mandatory; `make check` fails if forgotten (existing `test_config_schema.py` catches it) |
| Windows path encoding in `work_artifacts/` JSON | Medium | `_state.py` uses `encoding="utf-8"` explicitly on all read/write calls |
| Loop runs indefinitely if polling never times out | Low | `poll_timeout_seconds` is always enforced; `max_rounds` is a hard cap |
