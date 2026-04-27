# Feature Specification: Feedback-Based Signal Weight Calibration

**Feature Branch**: `001-calibrate-feedback`
**Created**: 2026-04-27
**Status**: Draft (reverse-engineered from existing implementation)
**Source**: `src/drift/calibration/`, `src/drift/commands/calibrate.py`

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Developer marks a finding as false positive (Priority: P1)

A developer runs `drift analyze` and sees a finding they know is wrong.
They want to record that verdict so future calibration rounds lower the
weight of that signal for their repository.

**Why this priority**: This is the primary feedback entry point. Without it, no
evidence accumulates and calibration produces no value.

**Independent Test**: Run `drift feedback mark --signal PFS --file src/foo.py --verdict fp`
and verify a new `FeedbackEvent` with `verdict="fp"` appears in `.drift/feedback.jsonl`.

**Acceptance Scenarios**:

1. **Given** a developer has a drift finding for signal `PFS` in `src/foo.py`,
   **When** they run `drift feedback mark --signal PFS --file src/foo.py --verdict fp`,
   **Then** a `FeedbackEvent` with `verdict="fp"`, `source="user"`, stable `finding_id`,
   and ISO-8601 timestamp is appended to `.drift/feedback.jsonl`.

2. **Given** a finding has already been marked in the same session,
   **When** the same finding is marked again with a different verdict,
   **Then** the duplicate is deduplicated on next `drift calibrate run` (lower-priority
   source loses; user always wins).

3. **Given** the `.drift/` directory does not exist,
   **When** a feedback event is recorded,
   **Then** the directory and file are created automatically without error.

---

### User Story 2 — Developer runs calibration and gets adjusted weights (Priority: P1)

After accumulating feedback events, a developer wants drift to recompute
signal weights that reflect their codebase's actual TP/FP ratio, reducing
noise from signals that are consistently wrong in their context.

**Why this priority**: Core value of the feature — turns feedback into lower noise.

**Independent Test**: Create a `.drift/feedback.jsonl` with ≥20 FP events for signal `AVS`,
run `drift calibrate run --dry-run`, verify output shows a negative delta for `AVS`
and `dry_run: true` in JSON format.

**Acceptance Scenarios**:

1. **Given** ≥`min_samples` feedback events exist for a signal,
   **When** `drift calibrate run` is executed,
   **Then** the calibrated weight for that signal deviates from the default,
   the confidence shown is ≥0 % and ≤100 %, and `drift.yaml` is updated with the
   new weight (unless `--dry-run` is set).

2. **Given** fewer than `min_samples` feedback events exist for a signal,
   **When** `drift calibrate run` is executed,
   **Then** the weight for that signal remains at default (graceful degradation).

3. **Given** no feedback events exist at all,
   **When** `drift calibrate run` is executed,
   **Then** the command exits with a user-friendly "No feedback evidence found" message
   and exit code 0.

4. **Given** `--dry-run` flag is set,
   **When** `drift calibrate run --dry-run` is executed,
   **Then** weight changes are displayed but `drift.yaml` is NOT modified and
   `.drift/calibration_status.json` is NOT written.

---

### User Story 3 — Developer inspects calibration evidence per signal (Priority: P2)

A developer wants to understand *why* drift recommends a specific weight
change — how many TP, FP, and FN events contributed, and how confident the
calibration is.

**Why this priority**: Transparency needed for trust; without it, developers cannot
validate whether calibration is working correctly.

**Independent Test**: With a populated `.drift/feedback.jsonl`, run `drift calibrate explain`
and verify output includes TP/FP/FN counts and Precision/Confidence values for at
least one signal.

**Acceptance Scenarios**:

1. **Given** feedback events for multiple signals exist,
   **When** `drift calibrate explain` is run,
   **Then** each signal with evidence shows `TP`, `FP`, `FN`, `Precision`, and
   `Confidence` in human-readable form.

2. **Given** no feedback events exist,
   **When** `drift calibrate explain` is run,
   **Then** output shows "No feedback evidence found" and exits with code 0.

---

### User Story 4 — Developer checks calibration status and freshness (Priority: P2)

A developer wants a quick overview: how many feedback events exist, where
the feedback file is, how many history snapshots are stored, and whether
auto-recalibration is active.

**Why this priority**: Operational visibility; needed for CI integrations and
troubleshooting stale calibration.

**Acceptance Scenarios**:

1. **Given** calibration is enabled in `drift.yaml`,
   **When** `drift calibrate status` is run,
   **Then** output shows event count, feedback path, snapshot count, `min_samples`,
   and auto-recalibrate status.

2. **Given** calibration is disabled in `drift.yaml`,
   **When** `drift calibrate status` is run,
   **Then** output clearly states calibration is not enabled and how to enable it.

---

### User Story 5 — Developer resets calibrated weights to defaults (Priority: P3)

A developer wants to undo all calibration and go back to the out-of-the-box weights
(e.g., after a major codebase restructure that invalidates old evidence).

**Why this priority**: Escape hatch; lower urgency than core feedback loop.

**Acceptance Scenarios**:

1. **Given** `drift.yaml` contains custom `weights:` entries,
   **When** `drift calibrate reset` is run,
   **Then** the `weights:` key is removed from `drift.yaml` and the defaults take effect.

2. **Given** `drift.yaml` contains no `weights:` entries,
   **When** `drift calibrate reset` is run,
   **Then** output states "No custom weights found" and the file is unchanged.

---

### Edge Cases

- What happens when `.drift/feedback.jsonl` contains malformed JSON lines?
  → Malformed lines are silently skipped; valid events are still processed.
- What happens when two evidence sources record the same finding with conflicting verdicts?
  → Source priority order applies: `user > inline_confirm/suppress > github_api > git_correlation`.
- What happens when `drift.yaml` is missing or unreadable during calibration?
  → Command exits with a clear error message referencing the missing config path.
- What happens when `drift.yaml` is present but not writable during a non-dry-run `calibrate run`?
  → Command MUST exit non-zero with a clear error message indicating the file is not writable; no partial write occurs.
- What happens when feedback events reference signal types not in the current signal registry?
  → Unknown signals are ignored; calibration proceeds for known signals.

---

## Clarifications

### Session 2026-04-27

- Q: Soll die Feedback-Datei repo-lokal und `.gitignore`d bleiben (nur Autor), oder auch geteilt/committed werden können? → A: Feedback ist repo-lokal und `.gitignore`d — kein Team-Sharing via VCS. Option C (lokale + geteilte Datei) ist außerhalb des Scope dieser Spec.
- Q: Was ist die Semantik von `auto_recalibrate`? Wird es automatisch getriggert oder nur angezeigt? → A: `auto_recalibrate` ist nur ein Konfigurationsfeld, das in `calibrate status` angezeigt wird; die Trigger-Logik (automatischer Aufruf von `drift calibrate run` durch `drift analyze`) liegt außerhalb des Scope dieser Spec.
- Q: Soll die Feedback-Datei unbegrenzt wachsen oder gibt es eine Größenbeschränkung? → A: Maximale Zeilenzahl ist konfigurierbar (`max_feedback_events` in `drift.yaml`); bei Überschreitung werden älteste Einträge (FIFO) entfernt, bevor neue angehängt werden.
- Q: Soll der `min_samples`-Default (20) als beobachtbarer Spec-Vertrag gelten oder als reines Implementierungsdetail? → A: Default=20 ist beobachtbarer Spec-Vertrag; Akzeptanztests dürfen diesen Wert als Ankerpunkt nutzen.
- Q: Was soll passieren, wenn `drift.yaml` bei einem nicht-dry-run `calibrate run` schreibgeschützt ist? → A: Hard fail mit Exit-Code ≠ 0 und klarer Fehlermeldung; kein partielles Schreiben.

---

## Requirements *(mandatory)*

<!--
  Constitution constraints (v1.0.0) that apply to every feature:
  - I. Library-First: calibration logic lives in src/drift/calibration/ (standalone library)
  - II. Test-First: acceptance scenarios above drive the initial failing tests
  - III. Functional: pure functions + frozen models; side effects isolated at CLI boundary
  - IV. CLI: calibrate Click group with run/explain/status/reset subcommands
  - V. Simplicity: Bayesian lerp is the simplest formula that degrades gracefully to defaults
-->

### Functional Requirements

- **FR-001**: Users MUST be able to record TP, FP, and FN verdicts for individual drift findings via CLI.
- **FR-001b**: The feedback file (`feedback.jsonl`) MUST be stored in a local, per-user path that is NOT committed to version control (`.gitignore`d by default). Team-shared feedback paths are out of scope.
- **FR-002**: Calibration MUST use a Bayesian lerp formula that blends default and precision-scaled weights proportionally to confidence (evidence count / `min_samples`). The default value of `min_samples` is **20** — this is an observable spec contract testable via acceptance tests.
- **FR-003**: Calibration confidence MUST range from 0 % (zero observations) to 100 % (`min_samples` or more observations); confidence MUST NOT exceed 1.0. With the default `min_samples=20`, exactly 20 observations yield confidence=1.0.
- **FR-004**: When fewer than `min_samples` events exist for a signal, its weight MUST remain at the default value.
- **FR-005**: Feedback events from multiple sources MUST be deduplicated; higher-priority source wins (`user > inline > github_api > git_correlation`).
- **FR-006**: Calibration output MUST support `text` and `json` formats for both human and machine consumption.
- **FR-007**: On `--dry-run`, no files MAY be modified (neither `drift.yaml` nor `.drift/calibration_status.json`).
- **FR-008**: `drift calibrate explain` MUST surface per-signal TP/FP/FN counts, observed precision, and confidence.
- **FR-009**: `drift calibrate status` MUST show event count, feedback path, snapshot count, `min_samples`, and the value of the `auto_recalibrate` config flag. The semantics of when `auto_recalibrate` triggers a calibration run are out of scope for this spec.
- **FR-010**: `drift calibrate reset` MUST remove only the `weights:` key from `drift.yaml`; all other config MUST remain unchanged.
- **FR-011**: All file writes MUST be atomic (write to temp, rename) to prevent partial corruption on crash.
- **FR-011b**: The feedback file MUST NOT grow beyond `max_feedback_events` lines (configurable in `drift.yaml` under `calibration.max_feedback_events`); when the limit is reached, the oldest entries MUST be removed (FIFO) before the new event is appended.
- **FR-011c**: If `drift.yaml` is not writable during a non-dry-run `calibrate run`, the command MUST exit non-zero with a clear error message; no weights are partially written.
- **FR-012**: The standalone calibration library (`src/drift/calibration/`) MUST be importable and fully functional without any CLI dependency.
- **FR-013**: Evidence from git-outcome correlation (auto-detected from scan history + defect-fix commits) MUST be merged into the feedback stream before calibration runs.
- **FR-014**: Calibration status metadata MUST be persisted to `.drift/calibration_status.json` after every non-dry-run calibration.

### Key Entities

- **FeedbackEvent**: A single evidence data point — `signal_type`, `file_path`, `verdict` (tp/fp/fn), `source`, `start_line`, `timestamp`, `finding_id` (stable SHA-256 prefix), `evidence` (arbitrary metadata).
- **SignalEvidence**: Aggregated TP/FP/FN counts + derived `precision` and `recall_indicator` for one signal.
- **CalibrationResult**: Output of `build_profile` — `calibrated_weights`, per-signal evidence map, per-signal confidence map, `total_events`, `signals_with_data`, plus `weight_diff()` method.
- **ScanSnapshot**: Point-in-time record of all findings (for retrospective correlation) — `timestamp`, `drift_score`, `finding_count`, `findings: list[FindingSnapshot]`.
- **SignalWeights**: Pydantic model from `drift.config` holding per-signal weight floats; used as both input (defaults) and output (calibrated) of `build_profile`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A developer can mark a finding and run calibration in under 60 seconds total, including `drift calibrate run` execution time.
- **SC-002**: With ≥20 feedback events for a signal, the calibrated weight differs meaningfully (|delta| > 0.0001) from the default when observed precision deviates by ≥10 percentage points.
- **SC-003**: Calibration produces no weight change (delta = 0) for any signal with fewer than `min_samples` (default: 20) observations — verified by unit test.
- **SC-004**: Deduplication ensures that running calibration twice on the same feedback file yields identical `weight_diff` output.
- **SC-005**: `drift calibrate run --format json` output is valid JSON and deserializable without error by standard parsers.
- **SC-006**: No `.drift/feedback.jsonl` or `.drift/calibration_status.json` write occurs when `--dry-run` is active — verifiable by file-system assertion in tests.

---

## Assumptions

- The signal registry is stable at calibration time; signals not in the current registry are ignored without error.
- `max_feedback_events` has a sensible default (e.g., 10 000); setting it to 0 or absent disables the cap.
- `drift.yaml` uses YAML format and is writable by the process running calibration.
- Git history access (for outcome correlation) is optional — calibration degrades gracefully when no `history_dir` exists.
- `min_samples` (default 20) and `fn_boost_factor` (default 0.1) are the correct domain defaults; they are configurable via `drift.yaml` under `calibration:`.
- The deprecated `github_correlator` and `outcome_correlator` modules are excluded from this specification; they will be removed in v3.0.
