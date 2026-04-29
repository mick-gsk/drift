# Implementation Plan: Feedback-Based Signal Weight Calibration

**Branch**: `main` | **Date**: 2026-04-27 | **Spec**: [specs/001-calibrate-feedback/spec.md](./spec.md)
**Input**: Feature specification from `specs/001-calibrate-feedback/spec.md`

## Summary

Enable developers to mark drift findings as TP/FP/FN via `drift feedback mark`,
then apply Bayesian weight calibration via `drift calibrate run`. The feature is
**substantially implemented** (14/16 FRs complete). This plan targets the two
open gaps: FR-011b (FIFO cap on feedback.jsonl) and FR-011c (hard fail when
drift.yaml is unwritable), using test-first development.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Click, Pydantic, Rich, PyYAML (existing stack — no new deps)
**Storage**: `.drift/feedback.jsonl` (FIFO-capped JSONL), `.drift/calibration_status.json` (JSON), `drift.yaml` (YAML)
**Testing**: pytest, mypy (strict), ruff
**Target Platform**: Local developer workstation (Linux / macOS / Windows)
**Project Type**: Library (`src/drift/calibration/`) + CLI extension (`src/drift/commands/calibrate.py`)
**Performance Goals**: SC-001: `drift feedback mark` + `drift calibrate run` completes in < 60 s
**Constraints**: Atomic writes only (no partial state); FIFO cap enforced in library layer; no network access
**Scale/Scope**: 1 developer, 1 repo, ~ 1 000 – 10 000 feedback events

## Constitution Check

*Pre-design gate: passes. Re-verified after Phase 1.*

- [x] **I. Library-First**: All calibration logic lives in `src/drift/calibration/`. CLI in
  `src/drift/commands/calibrate.py` delegates to the library — zero core logic in command layer.
  New FR-011b (FIFO cap) belongs in `record_feedback()` in `feedback.py`, not in the CLI. ✅
- [x] **II. Test-First**: Two gaps (FR-011b, FR-011c) require RED tests before implementation.
  Existing test suites (`tests/test_calibration*.py`) provide a foundation. New failing tests must
  be authored and reviewed before any implementation lines are written. ✅
- [x] **III. Functional Programming**: `build_profile()`, `load_feedback()`, and
  `dedupe_feedback_events()` are pure functions today. `record_feedback()` is the sole I/O sink.
  New FIFO-cap logic must remain co-located with the I/O boundary. ✅
- [x] **IV. CLI Interface & Observability**: All four subcommands (`run`, `explain`, `status`,
  `reset`) support `--format text/json` (where applicable) and clear Rich terminal output.
  Error paths produce machine-readable exit codes. ✅
- [x] **V. Simplicity & YAGNI**: Both gaps are directly required by accepted spec clarifications
  (Q3 → FIFO cap; Q5 → hard fail). No speculative abstractions are introduced.
  No new dependencies are required. ✅

**Constitution Gate: PASS** — proceed to Phase 1 design.

## Project Structure

### Documentation (this feature)

```text
specs/001-calibrate-feedback/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 output — all decisions resolved
├── data-model.md        # Phase 1 output — entity definitions
├── quickstart.md        # Phase 1 output — end-to-end usage guide
├── contracts/
│   └── cli-contract.md  # Phase 1 output — CLI + library API contract
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
src/drift/calibration/               # Library layer (FR-012: importable without CLI)
├── __init__.py                      # Exports: FeedbackEvent, build_profile,
│                                    #          load_feedback, record_feedback
├── feedback.py                      # FeedbackEvent dataclass, record_feedback,
│                                    # load_feedback, dedupe_feedback_events
│                                    #   ← FR-011b: add max_feedback_events param
├── profile_builder.py               # build_profile(), SignalEvidence, CalibrationResult
├── history.py                       # ScanSnapshot, load_snapshots
├── _atomic_io.py                    # Atomic write utilities
├── status.py                        # write_calibration_status
└── recommendation_calibrator.py    # RecommendationCalibrator (existing)

src/drift/commands/
└── calibrate.py                     # Click group: run, explain, status, reset
                                     #   ← FR-011c: add writability check in run()

src/drift/config.py                  # CalibrationConfig Pydantic model
                                     #   ← FR-011b: add max_feedback_events field

tests/
├── test_calibration_feedback.py     # Unit: record_feedback, load_feedback, dedupe
│                                    #   ← NEW: FIFO cap test (FR-011b RED first)
├── test_calibration_profile.py      # Unit: build_profile, weight_diff, SC-003/SC-004
├── test_calibration_cli.py          # CLI integration: run, explain, status, reset
│                                    #   ← NEW: unwritable drift.yaml test (FR-011c RED first)
└── test_calibration_sc.py           # Success criteria SC-001 through SC-006
```

**Structure Decision**: Existing single-package layout (`src/drift/`). No structural changes.
All new code is additive: one new config field, one new function param, one new guard clause.

## Complexity Tracking

No constitution violations. Both changes are minimal and justified by explicit spec
clarifications (Q3, Q5). No additional abstractions beyond the two targeted changes.

## Phase 0 Research Summary

See [research.md](./research.md) for full decision log.

**Key findings:**

1. **14 / 16 FRs already implemented** — this is a gap-fill task, not a full feature.
2. **FR-011b gap** (`record_feedback` has no FIFO cap):
   - Fix location: `src/drift/calibration/feedback.py` → `record_feedback(path, event, *, max_feedback_events=0)`
   - New config field: `CalibrationConfig.max_feedback_events: int = 0`
   - Logic: after append, if `max_feedback_events > 0` and `len(events) > max_feedback_events`, truncate to newest N
3. **FR-011c gap** (`calibrate run` raises raw OSError on unwritable drift.yaml):
   - Fix location: `_write_calibrated_weights()` caller in `run()` or inside the helper
   - Guard: `if not os.access(config_path, os.W_OK): raise click.ClickException(...)`

## Phase 1 Design Summary

See artefacts:
- [data-model.md](./data-model.md) — entity definitions, persistence mapping, calibration formula
- [contracts/cli-contract.md](./contracts/cli-contract.md) — CLI + library API contract
- [quickstart.md](./quickstart.md) — end-to-end usage guide

**Post-design Constitution re-check:**
All five principles still pass. No new entities, no new dependencies, no new abstractions.
