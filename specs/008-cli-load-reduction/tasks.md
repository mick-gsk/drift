# Tasks: CLI Load Reduction

**Input**: Design documents from [specs/008-cli-load-reduction](specs/008-cli-load-reduction)
**Prerequisites**: [specs/008-cli-load-reduction/plan.md](specs/008-cli-load-reduction/plan.md), [specs/008-cli-load-reduction/spec.md](specs/008-cli-load-reduction/spec.md), [specs/008-cli-load-reduction/research.md](specs/008-cli-load-reduction/research.md), [specs/008-cli-load-reduction/data-model.md](specs/008-cli-load-reduction/data-model.md), [specs/008-cli-load-reduction/contracts/cli-help-navigation.contract.md](specs/008-cli-load-reduction/contracts/cli-help-navigation.contract.md), [specs/008-cli-load-reduction/quickstart.md](specs/008-cli-load-reduction/quickstart.md)

**Tests**: Enthalten, da der Plan explizit Test-First sowie Contract- und Integrationstests fordert.

**Organization**: Tasks sind nach User Story organisiert, damit jede Story unabhängig implementierbar und testbar bleibt.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Arbeitsrahmen und Zielstruktur fuer die neue Help-Navigation vorbereiten

- [x] T001 Create vertical slice package scaffold in packages/drift-cli/src/drift_cli/help_nav/__init__.py
- [x] T002 [P] Create feature test package scaffold in tests/help_nav/__init__.py
- [x] T003 [P] Add help-nav test map entry in tests/TESTMAP.toml

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Kerninfrastruktur, die vor allen User Stories fertig sein muss

**Critical**: Keine Story-Implementierung vor Abschluss dieser Phase

- [x] T004 Define immutable data models CommandCapabilityArea, EntryPath, EntryStep, HelpSection in packages/drift-cli/src/drift_cli/help_nav/_models.py
- [x] T005 [P] Implement command-to-capability grouping primitives in packages/drift-cli/src/drift_cli/help_nav/_grouping.py
- [x] T006 [P] Implement help section rendering primitives for Rich and plain help content in packages/drift-cli/src/drift_cli/help_nav/_render.py
- [x] T007 [P] Implement compatibility guard helpers for legacy command paths in packages/drift-cli/src/drift_cli/help_nav/_compat.py
- [x] T008 Export public slice API only in packages/drift-cli/src/drift_cli/help_nav/__init__.py
- [x] T009 Add failing baseline unit tests for model and grouping invariants in tests/help_nav/test_help_nav_unit.py
- [x] T010 [P] Add failing baseline contract tests for help section presence/order in tests/help_nav/test_help_nav_contract.py
- [x] T011 [P] Add failing baseline integration tests for legacy command compatibility in tests/help_nav/test_help_nav_integration.py
- [x] T012 Wire help navigation entrypoint in root CLI registration in packages/drift-cli/src/drift_cli/cli.py
- [x] T036 Register explicit help-nav subcommand surface in packages/drift-cli/src/drift_cli/cli.py
- [x] T037 [P] Add contract test for help-nav subcommand exposure in tests/help_nav/test_help_nav_contract.py

**Checkpoint**: Foundation complete; all baseline tests exist and fail before story implementations

---

## Phase 3: User Story 1 - Schneller Einstieg ueber klares Help (Priority: P1) MVP

**Goal**: Ein klarer Start-hier-Pfad macht den Erstkontakt mit drift --help handlungsfaehig

**Independent Test**: Ein Erstnutzer kann nur mit drift --help den ersten Analyseweg finden und starten

### Tests for User Story 1

- [x] T013 [P] [US1] Add contract test for prominent start section visibility in tests/help_nav/test_help_nav_contract.py
- [x] T014 [P] [US1] Add contract test for minimal executable entry path steps in tests/help_nav/test_help_nav_contract.py
- [x] T015 [US1] Add integration test for first-run navigation flow from drift --help in tests/help_nav/test_help_nav_integration.py

### Implementation for User Story 1

- [x] T016 [US1] Implement Start-hier entry path builder for new users in packages/drift-cli/src/drift_cli/help_nav/_grouping.py
- [x] T017 [US1] Render Start-hier section as first help block in packages/drift-cli/src/drift_cli/help_nav/_render.py
- [x] T018 [US1] Integrate Start-hier section into CLI help composition in packages/drift-cli/src/drift_cli/cli.py
- [x] T019 [US1] Ensure user-facing wording for start guidance is concise and non-technical in packages/drift-cli/src/drift_cli/help_nav/_render.py

**Checkpoint**: User Story 1 ist eigenstaendig funktionsfaehig und testbar

---

## Phase 4: User Story 2 - Zielorientierte Navigation statt Befehlssuche (Priority: P2)

**Goal**: Nutzer navigieren ueber Aufgabenbereiche direkt zum passenden Command

**Independent Test**: Ein Nutzer findet Analyse- und Exportpfade ohne externe Doku nur ueber die Help-Struktur

### Tests for User Story 2

- [x] T020 [P] [US2] Add contract test for capability-area grouping presence in tests/help_nav/test_help_nav_contract.py
- [x] T021 [P] [US2] Add contract test for area purpose descriptions readability in tests/help_nav/test_help_nav_contract.py
- [x] T022 [US2] Add integration test for goal-to-command navigation hand-off in tests/help_nav/test_help_nav_integration.py
- [x] T042 [P] [US2] Add integration tests for narrow terminal widths (80/60/40 columns) in tests/help_nav/test_help_nav_integration.py
- [x] T044 [US2] Add contract assertions for initial-view section count and line caps in tests/help_nav/test_help_nav_contract.py

### Implementation for User Story 2

- [x] T023 [US2] Implement capability-area catalog and ordering rules in packages/drift-cli/src/drift_cli/help_nav/_grouping.py
- [x] T024 [US2] Implement navigation hand-off hints from overview to detail help in packages/drift-cli/src/drift_cli/help_nav/_render.py
- [x] T025 [US2] Add command reference mapping for analysis/reporting flows in packages/drift-cli/src/drift_cli/help_nav/_grouping.py
- [x] T026 [US2] Integrate grouped capability output into global help composition in packages/drift-cli/src/drift_cli/cli.py
- [x] T043 [US2] Implement narrow-width fallback formatting rules in packages/drift-cli/src/drift_cli/help_nav/_render.py

**Checkpoint**: User Story 2 ist eigenstaendig funktionsfaehig und testbar

---

## Phase 5: User Story 3 - Stabiler Betrieb fuer bestehende Workflows (Priority: P3)

**Goal**: Bestehende CLI-Aufrufe bleiben stabil, waehrend die neue Orientierungsschicht aktiv ist

**Independent Test**: Legacy-Aufrufe funktionieren unveraendert, neue Help-Navigation bleibt sichtbar

### Tests for User Story 3

- [x] T027 [P] [US3] Add integration test for unchanged legacy command invocation behavior in tests/help_nav/test_help_nav_integration.py
- [x] T028 [P] [US3] Add integration test for additive help changes without command removal in tests/help_nav/test_help_nav_integration.py
- [x] T029 [US3] Add contract test for stable top-level section naming/order for regression safety in tests/help_nav/test_help_nav_contract.py

### Implementation for User Story 3

- [x] T030 [US3] Implement legacy command compatibility checks in packages/drift-cli/src/drift_cli/help_nav/_compat.py
- [x] T031 [US3] Route compatibility checks into help composition workflow in packages/drift-cli/src/drift_cli/cli.py
- [x] T032 [US3] Ensure additive behavior guardrails in render pipeline in packages/drift-cli/src/drift_cli/help_nav/_render.py

**Checkpoint**: User Story 3 ist eigenstaendig funktionsfaehig und testbar

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Story-uebergreifende Konsolidierung und Validierung

- [x] T033 [P] Update quickstart verification commands and expectations in specs/008-cli-load-reduction/quickstart.md
- [x] T034 Document final help navigation behavior and examples in specs/008-cli-load-reduction/plan.md
- [x] T035 Run feature-focused test suite and capture summary in specs/008-cli-load-reduction/quickstart.md
- [x] T038 Capture baseline time-to-first-analysis metric protocol in specs/008-cli-load-reduction/quickstart.md
- [ ] T039 Capture post-change time-to-first-analysis and compute delta vs baseline (SC-002) in specs/008-cli-load-reduction/quickstart.md
- [ ] T040 Define and run first-use findability protocol for SC-001 in specs/008-cli-load-reduction/quickstart.md
- [ ] T041 Define and run clarity rating protocol for SC-004 in specs/008-cli-load-reduction/quickstart.md

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): Keine Abhaengigkeiten
- Foundational (Phase 2): Abhaengig von Phase 1; blockiert alle User Stories
- User Stories (Phase 3 bis Phase 5): Abhaengig von Phase 2
- Polish (Phase 6): Abhaengig von abgeschlossenen Stories

### User Story Dependencies

- US1 (P1): Startet direkt nach Phase 2
- US2 (P2): Startet nach Phase 2; keine harte Abhaengigkeit zu US1
- US3 (P3): Startet nach Phase 2; verifiziert additive Kompatibilitaet zu US1 und US2

### Within Each User Story

- Tests zuerst schreiben und fehlschlagen sehen
- Implementierung danach in Slice-Modulen
- CLI-Wiring erst nach Kernlogik
- Story mit eigenen Tests abschliessen, bevor naechste Story priorisiert wird

### Parallel Opportunities

- T002 und T003 parallel
- T005, T006, T007 parallel
- T010 und T011 parallel
- In US1: T013 und T014 parallel
- In US2: T020, T021 und T042 parallel
- In US3: T027 und T028 parallel

---

## Parallel Example: User Story 2

- Task: T020 Add contract test for capability-area grouping presence in tests/help_nav/test_help_nav_contract.py
- Task: T021 Add contract test for area purpose descriptions readability in tests/help_nav/test_help_nav_contract.py
- Task: T023 Implement capability-area catalog and ordering rules in packages/drift-cli/src/drift_cli/help_nav/_grouping.py

---

## Implementation Strategy

### MVP First (US1)

1. Phase 1 abschliessen
2. Phase 2 abschliessen
3. US1 vollstaendig umsetzen
4. US1 isoliert validieren
5. Danach erst US2/US3

### Incremental Delivery

1. Foundation bereitstellen
2. US1 liefern und validieren
3. US2 liefern und validieren
4. US3 liefern und validieren
5. Polish ausfuehren

### Parallel Team Strategy

1. Gemeinsamer Abschluss von Setup und Foundational
2. Danach parallele Story-Arbeit moeglich
3. Story-spezifische Tests halten Inkremente unabhaengig verifizierbar

---

## Notes

- Alle Tasks folgen dem Pflichtformat mit Checkbox, ID, optionalem P-Marker, optionalem Story-Label und Datei-Pfad
- Story-Labels sind nur in Story-Phasen gesetzt
- Tasks sind so formuliert, dass sie ohne Zusatzkontext direkt bearbeitet werden koennen
