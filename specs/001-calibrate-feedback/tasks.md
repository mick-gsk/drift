# Tasks: Feedback-Based Signal Weight Calibration

**Input**: Design documents from `specs/001-calibrate-feedback/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/cli-contract.md ✅, quickstart.md ✅

**Scope**: 14/16 FRs are already implemented. This task list targets the two open gaps:
- **FR-011b** — FIFO cap on `.drift/feedback.jsonl`
- **FR-011c** — Hard fail when `drift.yaml` is unwritable during `calibrate run`

**Constitution II (Test-First) is NON-NEGOTIABLE**: RED tests for FR-011b and FR-011c
MUST exist and fail before any implementation code is written.

---

## Format: `[ID] [P?] [Story?] Description with file path`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: User story this task belongs to (US1–US5, maps to spec.md)

---

## Phase 1: Setup

**Purpose**: Verify baseline — all existing calibration tests pass before any changes.

- [ ] T001 Run existing calibration test suite and confirm GREEN baseline: `python -m pytest tests/test_calibration.py tests/test_calibrate_cli_extended.py tests/test_issue_433_atomic_calibration_writes.py -q`

**Checkpoint**: Baseline is GREEN — all existing tests pass. Implementation environment is confirmed.

---

## Phase 2: Foundational — RED Tests (Constitution II: Test-First)

**Purpose**: Write failing tests for both gaps BEFORE any implementation.
Every task in this phase produces a test that MUST FAIL when run.

**⚠️ CRITICAL**: No implementation work (Phases 3–4) may begin until T002, T003, and T004 are complete.

- [ ] T002 [P] Create `tests/test_calibration_feedback.py` with a RED test for FR-011b: call `record_feedback()` with `max_feedback_events=3`, append 5 events, assert only the 3 newest remain in the JSONL file (test must FAIL — param does not exist yet)
- [ ] T003 [P] Create `tests/test_calibration_cli.py` with a RED test for FR-011c: create a temporary read-only `drift.yaml`, invoke `drift calibrate run` via Click test runner, assert non-zero exit code and error message containing "not writable" (test must FAIL — guard does not exist yet)
- [ ] T004 Run RED confirmation: `python -m pytest tests/test_calibration_feedback.py tests/test_calibration_cli.py -v` — confirm BOTH tests fail; abort if any test passes (a passing test means the gap is already fixed and the test is wrong)

**Checkpoint**: T002 and T003 are FAILING — RED phase confirmed. Implementation can begin.

---

## Phase 3: User Story 1 — `drift feedback mark` + FIFO Cap (Priority: P1) 🎯 MVP

**Goal**: Developer records TP/FP/FN feedback via `drift feedback mark`; feedback file is capped at `max_feedback_events` lines (FIFO, newest kept).

**Independent Test**: `drift feedback mark --signal PFS --file src/foo.py --verdict fp` →
new `FeedbackEvent` with `verdict="fp"` appears in `.drift/feedback.jsonl`;
with `max_feedback_events=3` configured and 5 total marks, only 3 newest events remain.

- [ ] T005 [US1] Add `max_feedback_events: int = Field(default=0, ...)` to `CalibrationConfig` in `src/drift/config/_schema.py` (after `max_snapshots` field; `extra="forbid"` is set so field MUST be explicitly added)
- [ ] T006 [US1] Add keyword-only `max_feedback_events: int = 0` parameter and FIFO cap logic to `record_feedback()` in `src/drift/calibration/feedback.py`: after append, if `max_feedback_events > 0` and line count exceeds cap, rewrite file keeping newest N events
- [ ] T007 [P] [US1] Wire `cfg.calibration.max_feedback_events` into all three `record_feedback()` call sites in `src/drift/commands/feedback.py` (lines ~93, ~289, ~362): pass as `max_feedback_events=cfg.calibration.max_feedback_events`
- [ ] T008 [US1] Run T002 test → GREEN; then run full calibration + feedback suite to confirm no regression: `python -m pytest tests/test_calibration_feedback.py tests/test_calibration.py tests/test_feedback_loop.py -v`

**Checkpoint**: US1 complete — `drift feedback mark` works; FIFO cap enforced; all existing tests still pass.

---

## Phase 4: User Story 2 — `drift calibrate run` + Write Guard (Priority: P1) 🎯 MVP

**Goal**: `drift calibrate run` on a non-writable `drift.yaml` exits non-zero with a clear error message; no partial write occurs. `--dry-run` is unaffected.

**Independent Test**: Mark `drift.yaml` read-only → `drift calibrate run` → exit code ≠ 0 and stderr contains "not writable"; `drift calibrate run --dry-run` on the same file → exit code 0.

- [ ] T009 [US2] Add `os.access()` pre-check + `click.ClickException` to `run()` in `src/drift/commands/calibrate.py`: resolve `actual_config` path (same logic as `_write_calibrated_weights`), check `if actual_config.exists() and not os.access(actual_config, os.W_OK)` before calling `_write_calibrated_weights()`, skip guard on `--dry-run` path
- [ ] T010 [US2] Run T003 test → GREEN; verify SC-006 (dry-run writes nothing) still holds: `python -m pytest tests/test_calibration_cli.py tests/test_issue_433_atomic_calibration_writes.py -v`

**Checkpoint**: US2 complete — FR-011c gap closed; both P1 user stories fully delivered.

---

## Phase 5: User Story 3 — `drift calibrate explain` (Priority: P2)

**Goal**: Per-signal TP/FP/FN counts, Precision, and Confidence are visible in output.

**Independent Test**: With a populated `.drift/feedback.jsonl`, `drift calibrate explain`
shows at least one signal row with TP/FP/FN and Confidence values.

- [ ] T011 [P] [US3] Add acceptance test for `drift calibrate explain` to `tests/test_calibrate_cli_extended.py`: create fixture with multi-signal feedback events, invoke `explain` via Click test runner, assert output contains "TP", "FP", "FN", "Precision", "Confidence" (or equivalent column headers in JSON mode)
- [ ] T012 [US3] Run T011 → GREEN (no implementation needed; confirm existing `explain` command covers it): `python -m pytest tests/test_calibrate_cli_extended.py -k "explain" -v`

**Checkpoint**: US3 acceptance criteria verified against existing implementation.

---

## Phase 6: User Story 4 — `drift calibrate status` (Priority: P2)

**Goal**: Quick overview: event count, feedback path, snapshot count, `min_samples`, `auto_recalibrate`.

**Independent Test**: `drift calibrate status` output contains all five required fields.

- [ ] T013 [P] [US4] Add acceptance test for `drift calibrate status` to `tests/test_calibrate_cli_extended.py`: create fixture with calibration config enabled, invoke `status` command, assert output contains event count, feedback path, snapshot count, `min_samples` value (default 20), and `auto_recalibrate` value
- [ ] T014 [US4] Run T013 → GREEN: `python -m pytest tests/test_calibrate_cli_extended.py -k "status" -v`; if any assertion fails, fix the missing field in `src/drift/commands/calibrate.py` (status subcommand output)

**Checkpoint**: US4 operational-visibility acceptance criteria confirmed.

---

## Phase 7: User Story 5 — `drift calibrate reset` (Priority: P3)

**Goal**: `weights:` key removed from `drift.yaml`; no other config touched.

**Independent Test**: `drift calibrate reset` removes the `weights:` block; running reset on a
config without custom weights prints "No custom weights found" and leaves file unchanged.

- [ ] T015 [P] [US5] Add acceptance tests for `drift calibrate reset` to `tests/test_calibrate_cli_extended.py`: (a) assert `weights:` key removed when present; (b) assert "No custom weights found" message and file unchanged when no `weights:` key
- [ ] T016 [US5] Run T015 → GREEN: `python -m pytest tests/test_calibrate_cli_extended.py -k "reset" -v`

**Checkpoint**: US5 escape-hatch acceptance criteria confirmed.

---

## Final Phase: Polish & Success Criteria

**Purpose**: Verify all six measurable success criteria from spec.md.

- [ ] T017 [P] Add/verify SC-003 test (no weight change below `min_samples=20`) in `tests/test_calibration.py`: provide 19 FP events for one signal, run `build_profile()`, assert `weight_diff()` returns 0 for that signal
- [ ] T018 [P] Add/verify SC-004 idempotency test in `tests/test_calibration.py`: run `build_profile()` twice on the same events, assert `calibrated_weights` are identical on both runs
- [ ] T019 [P] Add/verify SC-005 JSON-format test in `tests/test_calibrate_cli_extended.py`: invoke `drift calibrate run --format json --dry-run`, parse stdout with `json.loads()`, assert no exception is raised
- [ ] T020 [P] Add/verify SC-006 no-write-on-dry-run test in `tests/test_calibrate_cli_extended.py`: assert `drift.yaml` and `.drift/calibration_status.json` mtimes are unchanged after `drift calibrate run --dry-run`
- [ ] T021 Run full suite including mypy and ruff: `make check` — all green

**Checkpoint**: All success criteria verified. Feature implementation complete.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
  └─► Phase 2 (RED tests — BLOCKS all implementation)
        ├─► Phase 3 (US1 implementation — FR-011b)
        │     └─► Phase 4 (US2 implementation — FR-011c)  ← different files, can start once T004 done
        ├─► Phase 5 (US3 acceptance)  ← independent, can start after Phase 2
        ├─► Phase 6 (US4 acceptance)  ← independent, can start after Phase 2
        └─► Phase 7 (US5 acceptance)  ← independent, can start after Phase 2
              └─► Final Phase (polish + SC validation)
```

### User Story Dependencies

| Story | Priority | Implementation Gap | Depends On |
|-------|----------|--------------------|------------|
| US1   | P1       | FR-011b FIFO cap   | Phase 2 complete |
| US2   | P1       | FR-011c write guard| Phase 2 complete (US1 independent) |
| US3   | P2       | None (existing)    | Phase 2 complete |
| US4   | P2       | None (existing)    | Phase 2 complete |
| US5   | P3       | None (existing)    | Phase 2 complete |

US3, US4, and US5 can proceed in parallel with US1+US2 implementation (different files, read-only verification work).

### Within Phase 3 (US1)

```
T005 (config field) → T006 (function param) → T007 (wiring) → T008 (GREEN run)
```

T005 and T006 are sequential (T006 can reference the new field; T007 needs both).

### Parallel Opportunities

| Tasks | Why Parallelizable |
|-------|--------------------|
| T002, T003 | Different new test files, no shared dependencies |
| T007 | Wiring-only in `feedback.py`; independent of config/library edits in T005/T006 after those are done |
| T011, T013, T015 | Different US acceptance tests, all add to existing `test_calibrate_cli_extended.py` (serialize within file) |
| T017, T018, T019, T020 | All in `test_calibration.py` or `test_calibrate_cli_extended.py`; serialize within each file |

---

## Implementation Strategy

**MVP** (minimum to close both P1 gaps):
1. Complete Phase 1 → Phase 2 → Phase 3 → Phase 4.
2. At this point, both FR-011b and FR-011c are closed, P1 stories delivered.

**Incremental delivery**:
- After MVP: run Phase 5–7 (acceptance verification for already-implemented P2/P3 stories).
- Polish (Final Phase) independently per SC item.

**File change summary** (all changes additive or minimal):

| File | Change Type |
|------|-------------|
| `src/drift/config/_schema.py` | Add 1 field to `CalibrationConfig` |
| `src/drift/calibration/feedback.py` | Add 1 param + ~5 lines cap logic to `record_feedback()` |
| `src/drift/commands/feedback.py` | Wire `max_feedback_events` at 3 call sites |
| `src/drift/commands/calibrate.py` | Add ~4 lines write-guard before `_write_calibrated_weights()` |
| `tests/test_calibration_feedback.py` | **NEW**: FR-011b FIFO cap unit test |
| `tests/test_calibration_cli.py` | **NEW**: FR-011c write-guard CLI test |
| `tests/test_calibrate_cli_extended.py` | Add acceptance tests for US3, US4, US5, SC-005, SC-006 |
| `tests/test_calibration.py` | Add/verify SC-003, SC-004 unit tests |

---

## Summary

| Metric | Value |
|--------|-------|
| Total tasks | 21 |
| US1 tasks | 4 (T005–T008) |
| US2 tasks | 2 (T009–T010) |
| US3 tasks | 2 (T011–T012) |
| US4 tasks | 2 (T013–T014) |
| US5 tasks | 2 (T015–T016) |
| Setup + foundational | 4 (T001–T004) |
| Polish / SC validation | 5 (T017–T021) |
| New files | 2 (`test_calibration_feedback.py`, `test_calibration_cli.py`) |
| Files modified | 6 |
| New dependencies | 0 |

**Suggested MVP scope**: Phases 1–4 (T001–T010) — closes both P1 gaps with full TDD cycle.
