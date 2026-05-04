# Tasks: 006 Human Decision Cockpit

**Input**: Design documents from `/specs/006-human-decision-cockpit/`
**Prerequisites**: plan.md ✅ spec.md ✅ research.md ✅ data-model.md ✅ contracts/ ✅

---

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Kann parallel laufen (verschiedene Dateien, keine offenen Dependencies)
- **[Story]**: Zugehörige User Story (US1–US4)
- Alle Pfade relativ zum Repo-Root

---

## Phase 1: Setup

**Purpose**: Verzeichnisstruktur, Slice-Skeleton, CLI-Stub, Package-Registration

- [X] T001 Create vertical slice directory `src/drift/decision_cockpit/` with empty `__init__.py`
- [X] T002 [P] Create `tests/decision_cockpit/__init__.py` (empty)
- [X] T003 [P] Add `drift cockpit` Click group stub in `src/drift/decision_cockpit/_cmd.py` (import only, no logic)
- [X] T004 Register `cockpit` subcommand in `src/drift/commands/__init__.py` (or CLI entry point)
- [X] T005 [P] Create `.drift/cockpit/` ledger directory stub with `.gitkeep` (local artefact path for ledger JSON)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Frozen Pydantic models, failing test skeletons — MUSS vor allen User Stories abgeschlossen sein

**⚠️ KRITISCH**: Keine User-Story-Arbeit beginnen, bis dieser Block vollständig ist

- [X] T006 Implement all frozen Pydantic models in `src/drift/decision_cockpit/_models.py`: `DecisionBundle`, `DecisionRecord`, `RiskCluster`, `MinimalSafePlan`, `GuardrailCondition`, `LedgerEntry`, `OutcomeRecord`, `HumanOverride`; enums `DecisionStatus` (go / guardrails / no_go — **no** `pending_evidence`; missing evidence maps to `no_go` per spec clarification), `Verdict`, `OutcomeSignal`; domain exceptions `MissingEvidenceError`, `VersionConflictError`, `MissingOverrideJustificationError` in `src/drift/decision_cockpit/_exceptions.py`
- [X] T007 [P] Write failing test stubs for all acceptance scenarios (US1–US4) in `tests/decision_cockpit/test_status_engine.py`, `test_safe_plan.py`, `test_ledger_contract.py`, `test_cockpit_threshold_boundaries.py` — RED phase, alle Tests müssen fehlschlagen
- [X] T008 [P] Write failing contract test stubs for `LedgerEntry` and `DecisionBundle` invariants in `tests/decision_cockpit/test_cockpit_contracts.py` — RED phase
- [X] T009 [P] Implement JSON serialization for `DecisionBundle` (schema key `"decision-bundle-v1"`) in `src/drift/decision_cockpit/_output.py` stub

**Checkpoint**: Alle Modelle vorhanden, alle Tests rot, Slice-Skeleton fertig → US-Implementierung kann beginnen

---

## Phase 3: User Story 1 — Entscheidungsstatus in unter 2 Minuten (P1) 🎯 MVP

**Goal**: `drift cockpit build --pr <id>` liefert genau einen `DecisionStatus` mit Konfidenzwert und priorisierten Top-Risikotreibern

**Independent Test**: PR mit ausreichender Evidenz → `DecisionBundle` enthält genau einen Status, einen Konfidenzwert und mindestens einen Risikotreiber; Grenzwert-Inputs mappen deterministisch auf genau einen Status

- [X] T010 [US1] Implement `_status_engine.py`: pure function `compute_decision_status(confidence: float, has_evidence: bool) -> DecisionStatus` with fixed thresholds — go ≥ 0.85, guardrails 0.60–0.84, no_go < 0.60; missing evidence always returns `no_go`
- [X] T011 [US1] Implement `compute_confidence(signals: list[SignalResult]) -> float` (pure function) in `src/drift/decision_cockpit/_status_engine.py`
- [X] T012 [US1] Implement `prioritize_risk_drivers(signals: list[SignalResult]) -> list[RiskDriver]` (pure function, sorted by impact descending) in `src/drift/decision_cockpit/_status_engine.py`
- [X] T013 [US1] Implement `build_decision_bundle(pr_id: str, signals: list[SignalResult]) -> DecisionBundle` public function in `src/drift/decision_cockpit/__init__.py` — orchestrates status engine; raises `MissingEvidenceError` if no signals
- [X] T014 [US1] Implement `drift cockpit build` CLI command in `src/drift/decision_cockpit/_cmd.py`: `--pr`, `--repo`, `--format json|rich`, `--exit-zero`, `--output`
- [X] T015 [US1] Implement Rich output panel for `DecisionBundle` in `src/drift/decision_cockpit/_output.py`: status badge, confidence bar, top risk drivers table
- [X] T016 [US1] GREEN phase: make US1 unit tests pass (`test_status_engine.py`, `test_cockpit_threshold_boundaries.py`)
- [X] T017 [US1] Write integration test in `tests/decision_cockpit/test_cockpit_cmd_integration.py`: end-to-end CLI via `CliRunner` — go/guardrails/no_go/missing_evidence cases

---

## Phase 4: User Story 2 — Minimal Safe Change Set bewerten (P1)

**Goal**: `DecisionBundle` für No-Go- und Guardrails-PRs enthält mindestens einen `MinimalSafePlan` mit `risk_delta` und `score_delta`

**Independent Test**: No-Go-Fixture → `bundle.safe_plans` nicht leer; jeder Plan enthält `risk_delta < 0` und `score_delta > 0`; Guardrails-Fixture → Plan zeigt Delta relativ zur Go-Schwelle

- [X] T018 [US2] Implement `_safe_plan.py`: pure function `compute_safe_plans(bundle: DecisionBundle, signals: list[SignalResult]) -> list[MinimalSafePlan]` — greedy minimal cover; returns `[]` for go status
- [X] T019 [US2] Implement `compute_expected_deltas(plan: MinimalSafePlan, current_score: float, target_threshold: float) -> tuple[float, float]` (pure function, risk_delta + score_delta) in `src/drift/decision_cockpit/_safe_plan.py`
- [X] T020 [US2] Integrate `safe_plans` field into `build_decision_bundle()` in `src/drift/decision_cockpit/__init__.py`
- [X] T021 [US2] Add Minimal Safe Plan card to Rich output in `src/drift/decision_cockpit/_output.py`
- [X] T022 [US2] GREEN phase: make US2 unit tests pass (`test_safe_plan.py`)

---

## Phase 5: User Story 3 — Accountability Graph für Risikocluster (P2)

**Goal**: `DecisionBundle` enthält `RiskCluster`-Liste; jeder Cluster zeigt aggregierten Risikobeitrag zum Entscheidungsstatus

**Independent Test**: PR-Fixture mit mehreren Änderungspaketen → `bundle.risk_clusters` gruppiert Änderungen; dominanter Cluster steht an erster Position nach `risk_contribution` absteigend

- [X] T023 [US3] Implement `_cluster.py`: pure function `aggregate_clusters(signals: list[SignalResult], files: list[str]) -> list[RiskCluster]` — groups by signal category/file proximity; sorts by `risk_contribution` descending
- [X] T024 [US3] Integrate `risk_clusters` field into `build_decision_bundle()` in `src/drift/decision_cockpit/__init__.py`
- [X] T025 [US3] Add Accountability Graph section to Rich output in `src/drift/decision_cockpit/_output.py`: cluster list with contribution bars
- [ ] T026 [US3] Add `CockpitApp.tsx` React component scaffold in `playground/src/cockpit/CockpitApp.tsx` — renders Decision Panel from `DecisionBundle` JSON (status badge, confidence, risk drivers, clusters)
- [ ] T027 [US3] Add typed contract client `playground/src/cockpit/api.ts` — fetches `/cockpit/pr/{pr_id}/bundle` per `contracts/cockpit-api.yaml`
- [ ] T028 [US3] Add `RiskClusterGraph.tsx` component in `playground/src/cockpit/components/RiskClusterGraph.tsx` — visualizes cluster list
- [ ] T029 [US3] Write Vitest unit tests in `playground/src/cockpit/test/CockpitApp.test.tsx` for status badge rendering and cluster list rendering
- [X] T030 [US3] GREEN phase: make US3 Python unit tests pass (`test_status_engine.py` cluster assertions)

---

## Phase 6: User Story 4 — Entscheidungen und Outcomes nachverfolgen (P2)

**Goal**: `drift cockpit decide` schreibt einen `LedgerEntry` mit Empfehlung, menschlicher Entscheidung und Evidenzreferenz; Human Override nur mit Begründung; Outcomes nach 7/30 Tagen als `pending` → actual; Versionskonflikt bei Parallel-Edit

**Independent Test**: `LedgerEntry` mit `recommendation != human_decision` ohne `override_justification` → Fehler; fehlende Outcomes → `outcome_7d: pending`; zweite simultane Schreiboperation mit falschem `version` → HTTP 409 / `VersionConflictError`

- [X] T031 [US4] Implement `_ledger.py`: `write_ledger_entry(entry: LedgerEntry, path: Path) -> None` — append-only JSON write with optimistic locking (`version` field check before write; raise `VersionConflictError` on mismatch)
- [X] T032 [US4] Implement `read_ledger(pr_id: str, path: Path) -> list[LedgerEntry]` in `src/drift/decision_cockpit/_ledger.py`
- [X] T033 [US4] Implement `validate_override(entry: LedgerEntry) -> None` (pure function) in `src/drift/decision_cockpit/_ledger.py` — raise `MissingOverrideJustificationError` if `recommendation != human_decision` and `override_justification` is empty
- [X] T034 [US4] Implement `update_outcome(pr_id: str, outcome: OutcomeRecord, path: Path) -> None` — appends outcome to existing ledger entry; marks `outcome_7d`/`outcome_30d` field from `pending` to actual
- [X] T035 [US4] Implement `drift cockpit decide` CLI command in `src/drift/decision_cockpit/_cmd.py`: `--pr`, `--verdict`, `--justification`, `--repo`; calls `validate_override` + `write_ledger_entry`
- [X] T036 [US4] Implement `drift cockpit outcome` CLI command in `src/drift/decision_cockpit/_cmd.py`: `--pr`, `--outcome`, `--days 7|30`; calls `update_outcome`
- [ ] T037 [US4] Add Decision Timeline component in `playground/src/cockpit/components/DecisionTimeline.tsx` — renders ledger entries with recommendation, decision, justification, outcome status
- [ ] T038 [US4] Write Vitest tests in `playground/src/cockpit/test/DecisionTimeline.test.tsx` — pending outcome display, override justification display
- [X] T039 [US4] GREEN phase: make US4 Python unit tests pass (`test_ledger_contract.py` — override validation, version conflict, pending outcome)
- [X] T040 [US4] Write integration test `tests/decision_cockpit/test_cockpit_cmd_integration.py`: `decide` + `outcome` CLI flow end-to-end including conflict scenario

---

## Phase 7: Polish & Cross-Cutting

**Purpose**: Type checking, exit codes, FR-vollständigkeit, schema, docs

- [ ] T041 [P] Verify and fix all mypy type errors in `src/drift/decision_cockpit/` (`make check`)
- [ ] T042 [P] Verify exit codes for `drift cockpit build`: 0 = go, 1 = guardrails, 2 = no_go (includes missing-evidence case), 3 = system/runtime error, 10 = input validation error
- [ ] T043 [P] [US1] FR-009 versioning: **implement** version tracking in `build_decision_bundle()` — read existing version from `.drift/cockpit/<pr_id>.json` if present, else start at 1; increment by 1 on each rebuild for same `pr_id`; **add unit test** covering first-build (version=1) and re-build (version=n+1) cases
- [ ] T044 [P] [US1] FR-010 completeness: `drift cockpit build --format rich` renders all four panels (status + safe plan + clusters + ledger summary) in single invocation
- [ ] T045 [P] [US1] FR-012 threshold boundary test: parameterised pytest covering exact go/guardrails/no_go boundaries (0.849999, 0.850000, 0.599999, 0.600000) — no_go wins at exact lower boundary
- [ ] T046 [P] [US4] FR-014 pending sentinel: `LedgerEntry.outcome_7d` defaults to `OutcomeSignal.pending`; add schema test ensuring no `null` values in serialised ledger
- [ ] T047 [P] Update `src/drift/commands/__init__.py` to export `cockpit` command group; verify `drift --help` shows `cockpit`
- [ ] T048 [P] Add `drift cockpit` entry to `README.md` commands section and `docs/` quickstart (reference `specs/006-human-decision-cockpit/quickstart.md`)
- [ ] T049 [P] [US3] Add ground-truth TP/TN fixtures for cockpit cluster and status engine in `tests/fixtures/ground_truth.py` (precision-recall gate)
- [ ] T050 [P] [US4] Add ledger schema test: `LedgerEntry.model_json_schema()` matches expected JSON Schema for append-only audit invariants
- [X] T051 [P] [US1] Constitution IV — SARIF output: implement `--format sarif` for `drift cockpit build` in `src/drift/decision_cockpit/_output.py`; emit SARIF 2.1.0 with each `RiskDriver` mapped to a SARIF `result`; add test asserting valid SARIF structure

---

## Dependencies (User Story Completion Order)

```
Phase 1 (Setup) → Phase 2 (Foundational) → US1 (Phase 3) → US2 (Phase 4)
                                          → US3 (Phase 5, after US1)
                                          → US4 (Phase 6, after US1 + US2 models)
All → Phase 7 (Polish)
```

US2 and US3 can run concurrently after US1 Python core is green.  
US4 depends on US1 models and ledger path; can overlap US2/US3 frontend work.

---

## Parallel Execution Examples

### After Phase 2 completes:

```
Thread A: T010 → T011 → T012 → T013 → T014 → T015 → T016 → T017  (US1 Python)
Thread B: T018 → T019 → T020 → T021 → T022                        (US2 Safe Plan, after T013)
Thread C: T023 → T024 → T025 → T030                                (US3 Cluster Python, after T013)
Thread D: T026 → T027 → T028 → T029                                (US3 UI, after T013 JSON contract)
Thread E: T031 → T032 → T033 → T034 → T035 → T036 → T039 → T040  (US4 Ledger, after T006)
Thread F: T037 → T038                                               (US4 UI Timeline, after T027)
```

---

## Implementation Strategy

**MVP Scope (US1 only)**:  
Complete Phase 1 + Phase 2 + Phase 3 (T001–T017).  
Deliverable: `drift cockpit build --pr <id>` outputs a deterministic `DecisionBundle` with status, confidence, and risk drivers via JSON + Rich.

**Full V1**:  
Complete all phases including Ledger (US4) and UI (US3).  
Deliverable: Cockpit web view + CLI decision + outcome tracking with audit trail.

---

## Task Summary

| Phase | Tasks | User Story | Notes |
|-------|-------|-----------|-------|
| Setup | T001–T005 | — | Skeleton + CLI stub |
| Foundational | T006–T009 | — | Models + RED tests (blocking) |
| US1 | T010–T017 | P1 | Status engine + CLI (MVP) |
| US2 | T018–T022 | P1 | Safe Plan computation |
| US3 | T023–T030 | P2 | Cluster + React UI |
| US4 | T031–T040 | P2 | Ledger + Outcomes + UI Timeline |
| Polish | T041–T051 | — | Types, schema, docs, exit codes, SARIF |

**Total tasks**: 51  
**Parallel opportunities**: 26+ tasks marked [P]  
**MVP**: T001–T017 (17 tasks)  
**FR coverage**: FR-001–FR-015 vollständig abgedeckt  
**Constitution Principle II (Test-First)**: T007–T008 schreiben rote Tests vor jeder Implementierung in Phase 3–6  
**Constitution Principle IV (SARIF)**: T051 sichert SARIF-Output für CI/GitHub-Actions-Integration
