# Tasks: 005 Evidence-Based Drift Verification

**Input**: Design documents from `/specs/005-evidence-based-verification/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Kann parallel laufen (verschiedene Dateien, keine offenen Dependencies)
- **[Story]**: Zugehörige User Story (US1–US4)
- Alle Pfade relativ zum Repo-Root

---

## Phase 1: Setup

**Purpose**: Verzeichnisstruktur, Slice-Skeleton, Package-Registration

- [ ] T001 Create vertical slice directory `src/drift/verify/` with empty `__init__.py`
- [ ] T002 [P] Create `tests/verify/__init__.py` (empty)
- [ ] T003 [P] Add `drift verify` Click group stub in `src/drift/verify/_cmd.py` (import only, no logic)
- [ ] T004 Register `verify` subcommand in `src/drift/commands/__init__.py` (or CLI entry point)
- [ ] T005 [P] Create `scripts/generate_evidence_schema.py` stub (analogous to `scripts/generate_output_schema.py`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Frozen Pydantic models, failing test skeletons, schema skeleton — MUSS vor allen User Stories abgeschlossen sein

**⚠️ KRITISCH**: Keine User-Story-Arbeit beginnen, bis dieser Block vollständig ist

- [ ] T006 Implement all frozen Pydantic models in `src/drift/verify/_models.py`: `ChangeSet`, `EvidencePackage`, `ViolationFinding`, `ActionRecommendation`, `FunctionalEvidence`, `IndependentReviewResult`, `RulePromotionProposal`, `PatternHistoryEntry`, enums `ViolationType` / `Verdict` / `EvidenceFlag`
- [ ] T007 [P] Write failing test stubs for all acceptance scenarios (US1–US4) in `tests/verify/test_verify_unit.py` — RED phase, alle Tests müssen fehlschlagen
- [ ] T008 [P] Write failing contract test stubs for `EvidencePackage` invariants in `tests/verify/test_verify_contract.py` — RED phase
- [ ] T009 [P] Implement `ReviewerAgentProtocol` + `MockReviewerAgent` in `src/drift/verify/_reviewer.py`
- [ ] T010 [P] Implement `evidence_to_json()` JSON-Serialisierung (schema: `"evidence-package-v1"`) in `src/drift/verify/_output.py`
- [ ] T011 [P] Finalize `scripts/generate_evidence_schema.py` to emit JSON Schema for `EvidencePackage`; write schema to `drift.evidence.schema.json`
- [ ] T012 Add `drift.evidence.schema.json` to repo root (generated from T011)

**Checkpoint**: Alle Modelle vorhanden, alle Tests rot, Slice-Skeleton fertig → US-Implementierung kann beginnen

---

## Phase 3: User Story 1 — Vollständiges Evidenzpaket (P1) 🎯 MVP

**Goal**: `drift verify --diff <path>` liefert reproduzierbares Evidence Package mit Drift Score, Spec Confidence Score, Violations und `ActionRecommendation`

**Independent Test**: Synthetischer Diff → `EvidencePackage` geprüft auf Vollständigkeit (alle Pflichtfelder, reproduzierbarer Score, identisches Ergebnis bei zweitem Aufruf)

- [ ] T013 [US1] Implement `_checker.py`: `run_deterministic_checks(change_set) -> tuple[list[ViolationFinding], float]` — wraps `drift analyze` Python API (AVS/PFS/EDS signals)
- [ ] T014 [US1] Implement `compute_drift_score(violations) -> float` (pure function) in `src/drift/verify/_checker.py`
- [ ] T015 [US1] Implement `compute_spec_confidence(change_set, violations) -> float` (`passed_checks / total_checks`, deterministic) in `src/drift/verify/_checker.py`
- [ ] T016 [US1] Implement `build_action_recommendation(drift_score, spec_confidence, violations, flags) -> ActionRecommendation` (pure function) — all verdict decision logic
- [ ] T017 [US1] Implement public `verify(change_set, *, reviewer, ...) -> EvidencePackage` in `src/drift/verify/__init__.py` — orchestrates checker, reviewer (via protocol), promoter; handles empty diff → `no_changes_detected`
- [ ] T018 [US1] Implement `drift verify` CLI command in `src/drift/verify/_cmd.py`: `--diff`, `--repo`, `--spec`, `--format`, `--no-reviewer`, `--threshold-drift`, `--threshold-confidence`, `--exit-zero`, `--output`
- [ ] T019 [US1] Implement Rich output for `EvidencePackage` in `src/drift/verify/_output.py`: summary panel, verdict badge, violations table, scores
- [ ] T020 [US1] GREEN phase: make US1 unit tests pass (T007 stubs)
- [ ] T021 [US1] GREEN phase: make US1 contract tests pass (`EvidencePackage` invariants)
- [ ] T022 [US1] Write integration test `tests/verify/test_verify_integration.py` for end-to-end CLI invocation (subprocess/`CliRunner`) covering automerge + needs_fix + empty diff cases

---

## Phase 4: User Story 2 — Präzise Reparaturanweisungen (P2)

**Goal**: Jede `ViolationFinding` enthält `violation_type`, betroffene Datei/Zeile und konkrete `remediation`-Anweisung

**Independent Test**: Diff mit bekannter Layer-Verletzung → `ViolationFinding` enthält korrekten `violation_type`, Datei, Zeile und nicht-leere `remediation`

- [ ] T023 [US2] Implement `map_signal_finding_to_violation(finding: Finding) -> ViolationFinding` in `src/drift/verify/_checker.py` — maps AVS/PFS/EDS signal output to `ViolationType` + `remediation` text
- [ ] T024 [US2] Implement remediation message templates for all `ViolationType` variants (layer_violation, forbidden_dependency, file_placement, naming_convention) in `src/drift/verify/_checker.py`
- [ ] T025 [US2] Handle `rule_conflict` detection: when two signals produce contradicting verdicts for same file → emit `ViolationType.rule_conflict` with both `rule_id` and `conflicting_rule_id`; set `EvidenceFlag.rule_conflict`
- [ ] T026 [US2] GREEN phase: make US2 unit tests pass (remediation content, rule_conflict flag)

---

## Phase 5: User Story 3 — Independent Reviewer Agent (P3)

**Goal**: Nach deterministischem Check läuft `ReviewerAgentProtocol.review()` synchron; Ergebnis fließt als `confidence_delta` additiv in Spec Confidence Score; Timeout → `independent_review_unavailable`

**Independent Test**: Diff mit subtiler Spec-Abweichung → `IndependentReviewResult.available == True`, `findings` nicht leer; bei forciertem Timeout → `available == False`, `EvidenceFlag.independent_review_unavailable` gesetzt

- [ ] T027 [US3] Implement `DriftMcpReviewerAgent` in `src/drift/verify/_reviewer.py`: calls `drift.api.nudge` with timeout; returns `IndependentReviewResult(available=False, ...)` on timeout/error — no exception raised
- [ ] T028 [US3] Integrate `IndependentReviewResult.confidence_delta` into `verify()` public API: additive adjustment after deterministic spec confidence computation
- [ ] T029 [US3] Implement `--reviewer-timeout` and `--no-reviewer` CLI flags in `_cmd.py`; wire to `DriftMcpReviewerAgent` vs `MockReviewerAgent(unavailable)`
- [ ] T030 [US3] GREEN phase: make US3 unit tests pass (reviewer integration, timeout fallback, confidence_delta)

---

## Phase 6: User Story 4 — Rule Promotion (P4)

**Goal**: Wiederkehrendes Verletzungsmuster → `RulePromotionProposal` nach ≥ Schwellwert Vorkommen; Vorschlag erscheint in `EvidencePackage.rule_promotions`

**Independent Test**: Dasselbe Violation-Muster 5× in History → `rule_promotions` enthält Eintrag; < 5× → leer

- [ ] T031 [US4] Implement `PatternHistoryStore` in `src/drift/verify/_promoter.py`: `append(entry)` → JSONL-Append to `.drift/pattern_history.jsonl`; `load() -> list[PatternHistoryEntry]`; creates `.drift/` dir if missing
- [ ] T032 [US4] Implement `compute_promotions(history, violations, threshold) -> list[RulePromotionProposal]` (pure function) in `src/drift/verify/_promoter.py`
- [ ] T033 [US4] Integrate promoter into `verify()` public API: append new entries, compute proposals, attach to `EvidencePackage.rule_promotions`
- [ ] T034 [US4] Implement `--promote-threshold` CLI flag in `_cmd.py`
- [ ] T035 [US4] GREEN phase: make US4 unit tests pass (promotion threshold logic, JSONL persistence)

---

## Phase 7: Polish & Cross-Cutting

**Purpose**: Schema validation, type checking, exit codes, edge cases, docs

- [ ] T036 [P] Add `test_evidence_schema.py`: verifies `drift.evidence.schema.json` matches `EvidencePackage.model_json_schema()` byte-for-byte (analogous to `tests/test_config_schema.py`)
- [ ] T037 [P] Verify and fix all mypy type errors in `src/drift/verify/` (`make check`)
- [ ] T038 [P] Verify exit codes: 0 = automerge/exit-zero, 1 = needs_fix, 2 = needs_review, 3 = escalate_to_human, 10 = input error
- [ ] T039 [P] Edge case: multi-layer diff (changes in multiple layers simultaneously) → all layer violations reported; `action_recommendation` driven by highest severity (≥1 high/critical → needs_fix)
- [ ] T040 [P] Update `src/drift/commands/__init__.py` to export `verify` command; verify `drift --help` shows `verify`
- [ ] T041 [P] Add `drift verify` entry to `README.md` and `docs/` quickstart section (reference `specs/005-evidence-based-verification/quickstart.md`)
- [ ] T042 [P] [US1] Implement `--format sarif` output in `src/drift/verify/_output.py`: emit SARIF 2.1.0 with `runs[0].results` mapping each `ViolationFinding` to a SARIF `result` (Constitution IV)
- [ ] T043 [P] [US1/US2] Add ground-truth TP/TN fixtures for `verify` module in `tests/fixtures/ground_truth.py`: layer_violation, forbidden_dependency, naming_convention (for SC-002 / SC-003 precision-recall gate, Constitution II)
- [ ] T044 [P] [US1] Wire `FunctionalEvidence` as optional caller-provided input via `verify(change_set, functional_evidence=None, ...)` — `drift verify` does NOT invoke pytest/ruff internally (FR-006)
- [ ] T045 [P] [US1] Write latency regression test `tests/verify/test_verify_performance.py`: assert end-to-end `verify()` completes within 180 s on a synthetic diff; mark `@pytest.mark.slow`, skipped by default (SC-001)
- [ ] T046 [P] [US3] Create benchmark fixtures in `benchmarks/` for SC-006 measurement: known spec deviations invisible to deterministic check, used to measure ≥15pp detection lift from reviewer

---

## Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundational)
Phase 2 → Phase 3 (US1 — MVP)
Phase 3 → Phase 4 (US2) [US2 extends _checker.py built in US1]
Phase 3 → Phase 5 (US3) [US3 extends verify() built in US1]
Phase 3 → Phase 6 (US4) [US4 adds promoter to verify() built in US1]
Phase 4, 5, 6 → Phase 7 (Polish)
```

US2, US3, US4 sind nach Abschluss von Phase 3 (US1) **unabhängig voneinander parallelisierbar**.

---

## Parallel Execution Examples

### Nach Phase 2 (Foundational abgeschlossen):
- T013–T022 (US1) sequenziell

### Nach Phase 3 (US1 abgeschlossen):
- T023–T026 (US2) parallel zu T027–T030 (US3) parallel zu T031–T035 (US4)

### Nach Phase 4+5+6:
- T036–T041 (Polish) alle parallel

---

## Implementation Strategy

**MVP (Phase 1–3)**: `drift verify --diff <path> --no-reviewer` liefert vollständiges Evidence Package mit Drift Score, Spec Confidence, Violations und ActionRecommendation. Kein Reviewer-Agent, keine Rule-Promotion.

**Increment 2 (Phase 4)**: Präzise Reparaturanweisungen für alle ViolationType-Varianten.

**Increment 3 (Phase 5)**: Reviewer-Agent-Integration (synchron, Timeout-Fallback).

**Increment 4 (Phase 6)**: Rule-Promotion aus Verlaufshistorie.

**Increment 5 (Phase 7)**: Schema-Gate, alle Checks grün, Docs.
