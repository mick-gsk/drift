# Tasks: Agent PR Review Loop

**Input**: Design documents from `specs/004-agent-pr-review-loop/`
**Prerequisites**: plan.md ✓, spec.md ✓, data-model.md ✓, contracts/cli-pr-loop.md ✓
**Branch**: `feat/agent-pr-review-loop`
**Date**: 2026-04-30

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[US1–US4]**: User story label (from spec.md priorities)
- Exact file paths included in every task

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the vertical-slice directory skeleton and config extension before any tests or implementation.

- [X] T001 Create vertical slice directory `src/drift/pr_loop/` with empty `__init__.py`
- [X] T002 Create test directory `tests/pr_loop/` with empty `__init__.py`
- [X] T003 [P] Add `pr_loop:` section with defaults to `drift.yaml` (reviewers, max_rounds, poll_interval_seconds, poll_timeout_seconds)
- [X] T004 [P] Add `work_artifacts/pr-loop-*.json` pattern to `.gitignore`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config model extension + schema regen. Must complete before any user-story slice compiles.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete — `DriftConfig` and `drift.schema.json` must be in sync or all existing tests break.

- [X] T005 Add `PrLoopConfig` Pydantic model to `src/drift/config/_loader.py`
- [X] T006 Add `pr_loop: PrLoopConfig | None = None` field to `DriftConfig` in `src/drift/config/_loader.py`
- [X] T007 Regenerate `drift.schema.json`

**Checkpoint**: `make check` passes on non-pr-loop tests; `drift.schema.json` is in sync.

---

## Phase 3: User Story 1 — Agent creates a reviewable PR (Priority: P1) 🎯 MVP

**Goal**: After completing a task, the agent can run all local gates and open a well-formed GitHub PR without human intervention.

**Independent Test**: Execute a small isolated code change, confirm a GitHub PR exists, `make check` passes, and PR description is non-empty.

### Tests for User Story 1

- [X] T009 [P] [US1] Write failing tests in `tests/pr_loop/test_models_unit.py`
- [X] T010 [P] [US1] Write failing contract tests in `tests/pr_loop/test_gh_contract.py`

### Implementation for User Story 1

- [X] T008 [P] [US1] Implement frozen Pydantic models in `src/drift/pr_loop/_models.py`
- [X] T011 [US1] Implement `src/drift/pr_loop/_state.py`
- [X] T012 [US1] Implement `post_self_review()` in `src/drift/pr_loop/_gh.py`
- [X] T013 [US1] Implement self-review body builder in `src/drift/pr_loop/_engine.py`
- [X] T014 [US1] Add `--dry-run` precondition check to `src/drift/pr_loop/_cmd.py` stub

**Checkpoint**: `pytest tests/pr_loop/test_models_unit.py tests/pr_loop/test_gh_contract.py` all green; `drift pr-loop --help` shows correct usage.

---

## Phase 4: User Story 2 — Agent self-reviews diff and requests agent reviews (Priority: P1)

**Goal**: After PR creation, the agent posts a structured self-review comment and requests all configured reviewers; the loop blocks until all have responded.

**Independent Test**: After PR creation, confirm (a) self-review comment appears on PR, (b) each configured reviewer is requested, (c) agent blocks further action until reviewer responses arrive.

### Tests for User Story 2

- [X] T015 [P] [US2] Write failing tests in `tests/pr_loop/test_engine_unit.py`
- [X] T016 [P] [US2] Extend `tests/pr_loop/test_gh_contract.py`

### Implementation for User Story 2

- [X] T017 [US2] Implement `request_reviewers()` in `src/drift/pr_loop/_gh.py`
- [X] T018 [US2] Implement `poll_reviews()` in `src/drift/pr_loop/_engine.py`
- [X] T019 [US2] Implement `get_reviews()` in `src/drift/pr_loop/_gh.py`
- [X] T020 [US2] Implement `should_exit()`, `should_escalate()`, and `detect_contradiction()` in `src/drift/pr_loop/_engine.py`
- [X] T021 [US2] Implement `next_loop_state()` in `src/drift/pr_loop/_engine.py`

**Checkpoint**: `pytest tests/pr_loop/test_engine_unit.py` all green; polling logic correctly terminates on approval and timeout.

---

## Phase 5: User Story 3 — Agent responds to review feedback in a loop (Priority: P2)

**Goal**: When any reviewer requests changes, the agent reads all unresolved comments, addresses each in a new commit, re-requests reviews, and loops until all approve or max rounds is reached.

**Independent Test**: Inject a synthetic "Changes Requested" review comment; confirm agent produces a follow-up commit addressing it and re-requests review without human intervention.

### Tests for User Story 3

- [X] T022 [P] [US3] Write failing tests in `tests/pr_loop/test_engine_unit.py` (loop iteration, escalation, conflict)
- [X] T023 [P] [US3] Write failing tests in `tests/pr_loop/test_state_unit.py`

### Implementation for User Story 3

- [X] T024 [US3] Implement `collect_unresolved_comments()` in `src/drift/pr_loop/_engine.py`
- [X] T025 [US3] Implement `get_pr_comments()` in `src/drift/pr_loop/_gh.py`
- [X] T026 [US3] Implement `push_fix_commits()` in `src/drift/pr_loop/_gh.py`
- [X] T027 [US3] Implement `post_escalation_summary()` in `src/drift/pr_loop/_gh.py`
- [X] T028 [US3] Wire full loop in `src/drift/pr_loop/_engine.py`: `loop_until_approved(...)`
- [X] T029 [US3] Implement `run_local_gates()` in `src/drift/pr_loop/_gh.py`
- [X] T048 [US3] Implement `detect_merge_conflicts()` and `post_conflict_report()` in `src/drift/pr_loop/_gh.py`

**Checkpoint**: `pytest tests/pr_loop/` all green; `loop_until_approved` drives a full synthetic round-trip in tests.

---

## Phase 6: User Story 4 — Agent responds to human comments (Priority: P3)

**Goal**: When a human leaves a comment on the open PR, the agent reads it, addresses or explicitly defers it with a written reason, and continues the loop.

**Independent Test**: Post a comment manually to a test PR; confirm the agent produces a response commit or explanatory reply without re-opening unrelated work.

### Tests for User Story 4

- [X] T030 [P] [US4] Write failing tests in `tests/pr_loop/test_engine_unit.py` (human comments)

### Implementation for User Story 4

- [X] T031 [US4] Extend `collect_unresolved_comments()` in `src/drift/pr_loop/_engine.py` to distinguish human comments
- [X] T032 [US4] Implement `post_deferral_reply()` in `src/drift/pr_loop/_gh.py`
- [X] T033 [US4] Update self-review body builder in `src/drift/pr_loop/_engine.py` to include human comment sections

**Checkpoint**: Human comment flow is handled; `pytest tests/pr_loop/` still all green.

---

## Phase 7: CLI Subcommand & Output Rendering

**Purpose**: Wire the complete engine to the Click CLI and implement all output formats.

- [X] T034 Implement full Click subcommand in `src/drift/pr_loop/_cmd.py`: `drift pr-loop <PR_NUMBER>` with options `--repo`, `--config`, `--format (rich|json)`, `--dry-run`, `--exit-zero`; map `LoopExitStatus` to exit codes (APPROVED=0, ESCALATED=1, ERROR=2, precondition=3)
- [X] T035 [P] Implement Rich output renderer in `src/drift/pr_loop/_output.py`: per-round progress (gates, self-review, reviewer status, polling indicator, fix commits); final status line; use `console.print(markup=False)` for any text containing literal brackets (e.g., `[github-copilot[bot]]`)
- [X] T036 [P] Implement JSON output renderer in `src/drift/pr_loop/_output.py`: emit `{"pr_number": N, "status": "...", "rounds_completed": N, "unresolved_comments": [...], "exit_code": N}` matching schema in `contracts/cli-pr-loop.md`
- [X] T037 Export public API in `src/drift/pr_loop/__init__.py`: `loop_until_approved`, `LoopState`, `PrLoopConfig`
- [X] T038 Register `pr_loop_cmd` in drift CLI entry point (locate via `grep -r "add_command\|import.*_cmd" src/drift/cli.py` or equivalent registration file)
- [X] T039 Write CLI integration tests in `tests/pr_loop/test_cmd_integration.py`: test exit codes 0/1/2/3; test `--dry-run` produces no writes to `work_artifacts/`; test `--format json` output matches schema; test `--exit-zero` always exits 0

---

## Phase 8: Script Entry Point & Orchestration Skill

**Purpose**: Thin script wrapper and the Copilot agent SKILL.

- [X] T040 Implement `scripts/pr_review_loop.py` as thin wrapper: `from drift.pr_loop._cmd import main; import sys; sys.exit(main())`
- [X] T041 Write `.github/skills/drift-pr-review-loop/SKILL.md`: frontmatter with `name`, `description` (include trigger words: pr-loop, review loop, agent review, Ralph Wiggum loop), `applyTo`; body covers: preconditions (`gh auth status`, local gates, PR number), Step 1 (`drift pr-loop <PR_NUMBER> --format json`), Step 2 (exit code interpretation), Step 3 (escalation handling from `work_artifacts/pr-loop-<PR>.json`), stop condition; reference spec FR-001–FR-013 as Single Source of Truth; no duplication of spec prose

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, CHANGELOG, final gate verification.

- [X] T042 Write `specs/004-agent-pr-review-loop/quickstart.md`: minimal how-to for agents (install check, `drift.yaml` snippet, one-liner invocation, expected output)
- [X] T043 Add CHANGELOG entry via `make changelog-entry COMMIT_TYPE=feat MSG='add drift pr-loop command: agent-driven PR review loop (FR-001–FR-013)'` — do NOT hand-format
- [X] T044 Create feature evidence artifact `benchmark_results/v<VERSION>_agent-pr-review-loop_feature_evidence.json` using the `drift-evidence-artifact-authoring` skill (required for `make gate-check COMMIT_TYPE=feat`)
- [X] T045 [P] Run `pre-commit run --all-files` and fix all findings (secrets, typos, shellcheck, EOF)
- [X] T046 [P] Run `make check` (lint + typecheck + pytest + self-analysis) and fix all failures
- [X] T047 Run `make gate-check COMMIT_TYPE=feat` and confirm all pre-push gates pass

---

## Dependency Graph (User Story Order)

```
Phase 1 (Setup)
  └── Phase 2 (Foundation / Config + Schema)
        ├── Phase 3 (US1 — PR creation + self-review) ─ MVP
        │     └── Phase 4 (US2 — reviewer requests + polling)
        │           └── Phase 5 (US3 — feedback loop) ─ Core Loop
        │                 └── Phase 6 (US4 — human comments)
        │                       └── Phase 7 (CLI + Output)
        │                             └── Phase 8 (Script + SKILL)
        │                                   └── Phase 9 (Polish)
        └── [T005–T008 block all downstream work]
```

## Parallel Execution Opportunities

| Round | Tasks runnable in parallel |
|-------|---------------------------|
| After T001–T002 | T003, T004 (gitignore + yaml) |
| After T005–T007 | T009, T010 (model tests + contract tests); then T008 [P] after tests exist |
| Phase 4 | T015, T016 (engine tests + gh contract extension) |
| Phase 5 | T022, T023 (engine loop tests + state tests) |
| Phase 7 | T035, T036 (Rich + JSON renderers); T034 is sequential (wires both) |
| Phase 9 | T045, T046 (pre-commit + make check) |

## Implementation Strategy

**MVP Scope** (Phases 1–4 + Phase 7 stub): US1 + US2 deliver the core value — agent creates PR, self-reviews, requests Copilot review, and blocks until response. This is usable and testable without the full feedback loop (US3).

**Full Loop** (Phases 5–8): US3 adds the iterative fix-and-re-review cycle. Deliver after MVP is stable.

**Total Tasks**: 48
**Tasks by User Story**: US1: 7, US2: 7, US3: 9, US4: 4, CLI/Infra: 15, Polish: 6
**Parallel opportunities**: 12 tasks marked [P]

## Format Validation

All 47 tasks follow the checklist format: `- [ ] T### [P?] [Story?] Description with file path`. No task is missing a checkbox, ID, or file path reference.
