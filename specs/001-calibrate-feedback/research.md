# Research: Feedback-Based Signal Weight Calibration

**Phase 0 output for** `specs/001-calibrate-feedback/plan.md`
**Date**: 2026-04-27
**Status**: Complete — all NEEDS CLARIFICATION items resolved

---

## 1. Existing Implementation Audit

### Decision: Feature is substantially implemented (≥87 % FR coverage)

**Rationale**: The calibration module (`src/drift/calibration/`) and the
`drift calibrate` Click group (`src/drift/commands/calibrate.py`) already satisfy
14 of the 16 functional requirements. The spec is reverse-engineered from working code.

**Evidence mapping:**

| FR | Status | Source |
|----|--------|--------|
| FR-001 | ✅ Implemented | `drift feedback mark` command + `record_feedback()` |
| FR-001b | ✅ Implemented | `resolve_feedback_paths()` returns local `.drift/feedback.jsonl` |
| FR-002 | ✅ Implemented | `build_profile()` Bayesian lerp, `min_samples=20` default |
| FR-003 | ✅ Implemented | `confidence = min(count / min_samples, 1.0)` |
| FR-004 | ✅ Implemented | Zero weight change below min_samples threshold |
| FR-005 | ✅ Implemented | `dedupe_feedback_events()` with `_SOURCE_PRIORITY` dict |
| FR-006 | ✅ Implemented | `--format text/json` on `calibrate run` |
| FR-007 | ✅ Implemented | `--dry-run` flag suppresses all file writes |
| FR-008 | ✅ Implemented | `calibrate explain` shows TP/FP/FN/Precision/Confidence |
| FR-009 | ✅ Implemented | `calibrate status` shows all required fields |
| FR-010 | ✅ Implemented | `calibrate reset` removes only `weights:` key atomically |
| FR-011 | ✅ Implemented | `_atomic_write_text()` and `_atomic_io.py` |
| FR-011b | ❌ **GAP** | `record_feedback()` appends unconditionally — no FIFO cap |
| FR-011c | ❌ **GAP** | `_write_calibrated_weights()` doesn't pre-check writability |
| FR-012 | ✅ Implemented | `drift.calibration` package importable without CLI |
| FR-013 | ✅ Implemented | `_collect_git_correlation()` in calibrate command |
| FR-014 | ✅ Implemented | `write_calibration_status()` in non-dry-run path |

---

## 2. Gap Analysis

### Gap 1: FR-011b — `max_feedback_events` FIFO Cap

**Problem**: `record_feedback()` in `src/drift/calibration/feedback.py` appends
every new event unconditionally. Feedback files can grow without bound on long-lived
repos with frequent `drift feedback mark` usage.

**Decision**: Add FIFO cap to `record_feedback()`.
- Read current file, apply cap, write back atomically when limit exceeded.
- Default: 10 000 events (configurable via `calibration.max_feedback_events` in `drift.yaml`).
- Setting to `0` or absent disables the cap.
- Cap is applied AFTER deduplication for accuracy.

**Rationale**: YAGNI is satisfied — real repos accumulate events over years; 10 000 is
large enough to avoid false-positive truncation and small enough to keep I/O fast.
Alternatively considered: no cap (Option A, simpler) — rejected because spec Q3 answer
explicitly chose Option B.

**Implementation location**: `src/drift/calibration/feedback.py` → `record_feedback()`
signature addition: `max_feedback_events: int = 0`.

### Gap 2: FR-011c — Hard Fail on Unwritable `drift.yaml`

**Problem**: `_write_calibrated_weights()` in the calibrate command calls
`_atomic_write_text()` which raises `OSError` on permission errors, but the error is
not caught and surfaced as a user-friendly message with a non-zero exit code.
Currently, the user sees a raw Python traceback.

**Decision**: Wrap the write path in an explicit pre-check (`os.access(path, os.W_OK)`)
and raise `click.ClickException` with a clear message before attempting the write.

**Rationale**: CLI error handling at system boundary — the alternative (catch OSError
and exit non-zero) is equivalent but a pre-check is cleaner and avoids partial-write risk
entirely.

**Implementation location**: `src/drift/commands/calibrate.py` → `_write_calibrated_weights()`
or its call site in `run()`.

---

## 3. Technology Choices

### Bayesian Lerp Formula (existing, confirmed)

```
confidence = min(count / min_samples, 1.0)
calibrated_weight = lerp(default_weight, precision_scaled_weight, confidence)
```

- `precision_scaled_weight = default_weight * observed_precision`
- `fn_boost_factor = 0.1` adjusts weight for FN-heavy signals
- No alternatives considered — formula is already live in production and validated.

### JSONL Persistence (existing, confirmed)

- Format: one JSON object per line, UTF-8, `sort_keys=True`
- Append-only with FIFO cap for `feedback.jsonl`
- Atomic write for `calibration_status.json` and `drift.yaml`

### Config Integration (existing, confirmed)

Relevant `drift.yaml` keys under `calibration:`:
```yaml
calibration:
  enabled: true
  min_samples: 20          # observable spec contract (default: 20)
  fn_boost_factor: 0.1
  history_dir: .drift/history
  auto_recalibrate: false  # display-only flag; trigger logic out of scope
  max_feedback_events: 0   # 0 = no cap; NEW (FR-011b)
```

---

## 4. Alternatives Considered

| Decision | Chosen | Rejected | Reason |
|----------|--------|----------|--------|
| Feedback cap | FIFO (keep newest) | FIFO keep oldest | Newer feedback more representative of current codebase state |
| Write-fail mode | Hard fail (exit ≠ 0) | Warn + continue | Silent failure hides calibration not applied (spec Q5 answer) |
| Max events default | 10 000 | 1 000 / unlimited | 1000 too small for active repos; unlimited contradicts spec Q3 answer |
| Cap implementation | In `record_feedback()` | In CLI command | Library-First (Constitution §I): cap is a library concern |

---

## 5. Resolved NEEDS CLARIFICATION Items

All clarification questions from `spec.md → ## Clarifications / ### Session 2026-04-27`:

| # | Question | Resolution |
|---|----------|------------|
| Q1 | Team sharing via VCS? | Out of scope — local `.gitignore`d only |
| Q2 | `auto_recalibrate` semantics? | Display-only flag; trigger logic out of scope |
| Q3 | Feedback file size limit? | `max_feedback_events` FIFO cap, default 10 000 |
| Q4 | `min_samples=20` as spec contract? | Yes — observable, testable default |
| Q5 | Unwritable `drift.yaml`? | Hard fail, exit ≠ 0, no partial write |
