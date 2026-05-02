# Tasks: Complete VSA Migration

**Input**: Design documents from /specs/009-complete-vsa-migration/
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/migration-boundary.contract.md, quickstart.md

## Format: [ID] [P?] [Story] Description

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Arbeitsgrundlage und Artefaktstruktur fuer die Migrationsausfuehrung herstellen.

- [X] T001 Erstelle Migrations-Tracking-Dokument in work_artifacts/vsa_migration_inventory.md
- [X] T002 Erstelle Import-Mapping-Matrix in work_artifacts/vsa_import_mapping.csv
- [X] T003 [P] Erstelle Verifikationsskript-Rahmen in scripts/migration/audit_legacy_paths.py
- [X] T004 [P] Erstelle Verifikationsskript-Rahmen in scripts/migration/check_import_boundaries.py
- [X] T005 Ergaenze Ausfuehrungshinweise fuer Migrationstools in ./DEVELOPER.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Blockierende Voraussetzungen schaffen, bevor User-Story-Umsetzung startet.

**CRITICAL**: Keine User-Story-Arbeit vor Abschluss dieser Phase.

- [ ] T006 Implementiere Legacy-Pfad-Inventur in scripts/migration/audit_legacy_paths.py
- [ ] T007 Implementiere Import-Grenzpruefung fuer kanonische Paketpfade in scripts/migration/check_import_boundaries.py
- [ ] T008 [P] Erstelle Validierungsfixture fuer LegacyPath/ImportMapping in tests/migration/test_migration_models.py
- [ ] T009 [P] Erstelle Contract-Check fuer MigrationBoundary in tests/migration/test_migration_contract.py
- [ ] T010 Definiere kanonische Capability-Ownership-Tabelle in docs/architecture/vsa-monorepo.md
- [ ] T011 Ergaenze CI/Gate-Ausfuehrungsreihenfolge fuer Migrationsabschluss in work_artifacts/vsa_migration_inventory.md

**Checkpoint**: Baseline-Audits und Foundation-Checks sind verfuegbar, User Stories koennen umgesetzt werden.

---

## Phase 3: User Story 1 - Konsistente Paketnavigation (Priority: P1) 🎯 MVP

**Goal**: Contributor finden aktive Implementierung ausschliesslich in Capability-Paketen.

**Independent Test**: Ein Contributor lokalisiert und aendert eine repräsentative Capability ohne Nutzung von src/drift als aktive Implementierungsquelle.

### Implementation for User Story 1

- [ ] T012 [US1] Fuehre Legacy-Inventur aus und dokumentiere aktive Restpfade in work_artifacts/vsa_migration_inventory.md
- [ ] T013 [P] [US1] Migriere verbleibende aktive Session- und Orchestration-Implementierungen von src/drift nach packages/drift-session/src/drift_session/
- [ ] T014 [P] [US1] Migriere verbleibende aktive CLI-bezogene Implementierungen von src/drift nach packages/drift-cli/src/drift_cli/
- [ ] T015 [P] [US1] Migriere verbleibende aktive Engine-/Signal-Implementierungen von src/drift nach packages/drift-engine/src/drift_engine/
- [ ] T016 [US1] Entferne oder neutralisiere aktive Implementierungsreste unter src/drift/
- [ ] T017 [US1] Aktualisiere package-level Exporte fuer kanonische Pfade in packages/drift/src/drift/__init__.py
- [ ] T018 [US1] Aktualisiere Architekturuebersicht auf finalen Zustand in docs/architecture/vsa-monorepo.md
- [ ] T019 [US1] Aktualisiere Contributor-Navigation in ./README.md

**Checkpoint**: User Story 1 ist erfuellt, wenn keine aktive Implementierung mehr aus src/drift genutzt wird und Navigationsdoku konsistent ist.

---

## Phase 4: User Story 2 - Verlaesslicher Agenten-Workflow (Priority: P2)

**Goal**: Agenten arbeiten gegen einen eindeutigen, kanonischen Codepfad je Slice.

**Independent Test**: Symbolsuche und Patch-Erstellung zeigen nur kanonische Package-Pfade als aktive Implementierungsziele.

### Implementation for User Story 2

- [ ] T020 [US2] Normalisiere interne Runtime-Importe auf Capability-Paketpfade in packages/drift/src/drift/
- [ ] T021 [P] [US2] Normalisiere Importe in CLI-Kommandos auf kanonische Pfade in packages/drift-cli/src/drift_cli/commands/
- [ ] T022 [P] [US2] Normalisiere Importe in MCP-Routern auf kanonische Pfade in packages/drift-mcp/src/drift_mcp/
- [ ] T023 [P] [US2] Normalisiere Importe in Output-Layern auf kanonische Pfade in packages/drift-output/src/drift_output/
- [ ] T024 [US2] Ergaenze automatisierte Import-Grenztests in tests/migration/test_import_boundaries.py
- [ ] T025 [US2] Ergaenze Agenten-Referenz auf kanonische Bearbeitungspfade in ./AGENTS.md
- [ ] T026 [US2] Aktualisiere aktive Plan-/Arbeitsnavigation fuer Agenten in .github/copilot-instructions.md

**Checkpoint**: User Story 2 ist erfuellt, wenn Importpruefungen und Agenten-Navigation keine aktiven Legacy-Pfade mehr verwenden.

---

## Phase 5: User Story 3 - Niedrigere Onboarding-Huerde (Priority: P3)

**Goal**: Neue Contributor verstehen Paketgrenzen und Einstiegspfade ohne Nachfragen.

**Independent Test**: Ein Onboarding-Durchlauf fuehrt reproduzierbar zum korrekten Zielpaket fuer eine Beispielaenderung.

### Implementation for User Story 3

- [ ] T027 [US3] Erstelle Onboarding-Abschnitt zu Capability-Grenzen in docs-site/getting-started.md
- [ ] T028 [P] [US3] Erstelle Kurzreferenz fuer Paketzuordnung in docs-site/architecture.md
- [ ] T029 [P] [US3] Aktualisiere DEVELOPER-Workflow fuer kanonische Pfadwahl in ./DEVELOPER.md
- [ ] T030 [US3] Erstelle verifizierbaren Onboarding-Checkablauf in work_artifacts/vsa_onboarding_checklist.md
- [ ] T037 [US3] Definiere Onboarding-Messprotokoll (N=10, Erfolgskriterium, Abbruchkriterium) in work_artifacts/vsa_onboarding_checklist.md
- [ ] T038 [P] [US3] Erfasse Onboarding-Durchlaeufe und Resultate in work_artifacts/vsa_onboarding_results.csv
- [ ] T039 [US3] Berechne Erfolgsquote und dokumentiere SC-003-Nachweis in work_artifacts/vsa_migration_inventory.md
- [ ] T031 [US3] Ergaenze Regressionstest fuer Legacy-Navigation in tests/migration/test_no_active_src_drift.py

**Checkpoint**: User Story 3 ist erfuellt, wenn Onboarding-Dokumentation und Checkablauf reproduzierbar zum richtigen Capability-Paket fuehren.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Abschlussverifikation und nachhaltige Absicherung ueber alle Stories.

- [ ] T032 [P] Fuehre `make check` aus und dokumentiere Ergebnis in work_artifacts/vsa_migration_inventory.md
- [ ] T033 Fuehre `make gate-check COMMIT_TYPE=feat` aus und dokumentiere Ergebnis in work_artifacts/vsa_migration_inventory.md
- [ ] T040 [P] Fuehre scripts/migration/audit_legacy_paths.py aus und dokumentiere active_legacy_impl_count in work_artifacts/vsa_migration_inventory.md
- [ ] T041 [P] Fuehre scripts/migration/check_import_boundaries.py aus und dokumentiere import_drift_violations in work_artifacts/vsa_migration_inventory.md
- [ ] T034 [P] Aktualisiere Abschlussstatus und Kriterien in work_artifacts/vsa_migration_inventory.md
- [ ] T035 [P] Dokumentiere Abschluss der Monorepo-Migration in ./CHANGELOG.md
- [ ] T036 Fuehre Quickstart-Validierung der Migrationsschritte in specs/009-complete-vsa-migration/quickstart.md durch

---

## Dependencies & Execution Order

### Phase Dependencies

- Setup (Phase 1): keine Abhaengigkeiten, sofort startbar.
- Foundational (Phase 2): haengt von Phase 1 ab und blockiert alle User Stories.
- User Stories (Phase 3 bis 5): starten nach Abschluss von Phase 2.
- Polish (Phase 6): startet nach den ausgewaehlten User Stories.

### User Story Dependencies

- US1 (P1): startet nach Phase 2, keine fachliche Abhaengigkeit auf andere Stories.
- US2 (P2): startet nach Phase 2; sollte auf US1-Ergebnissen fuer Importnormalisierung aufbauen, bleibt aber eigenstaendig validierbar.
- US3 (P3): startet nach Phase 2; nutzt den stabilisierten Zielzustand fuer Onboarding und Doku.

### Within Each User Story

- Inventur/Mapping vor Pfad- oder Importaenderungen.
- Pfad- und Importumstellung vor Dokumentationsfinalisierung.
- Story-Checkpoint vor naechster Prioritaetsstory.

### Parallel Opportunities

- T003 und T004 koennen parallel laufen.
- T008 und T009 koennen parallel laufen.
- In US1 koennen T013, T014 und T015 parallel laufen.
- In US2 koennen T021, T022 und T023 parallel laufen.
- In US3 koennen T028, T029 und T038 parallel laufen.
- In Polish koennen T032, T034, T035, T040 und T041 parallel laufen.

---

## Parallel Example: User Story 1

- Task: T013 [US1] Migriere Session- und Orchestration-Implementierungen in packages/drift-session/src/drift_session/
- Task: T014 [US1] Migriere CLI-bezogene Implementierungen in packages/drift-cli/src/drift_cli/
- Task: T015 [US1] Migriere Engine-/Signal-Implementierungen in packages/drift-engine/src/drift_engine/

## Parallel Example: User Story 2

- Task: T021 [US2] Normalisiere CLI-Importe in packages/drift-cli/src/drift_cli/commands/
- Task: T022 [US2] Normalisiere MCP-Importe in packages/drift-mcp/src/drift_mcp/
- Task: T023 [US2] Normalisiere Output-Importe in packages/drift-output/src/drift_output/

## Parallel Example: User Story 3

- Task: T028 [US3] Erstelle Paketzuordnungs-Kurzreferenz in docs-site/architecture.md
- Task: T029 [US3] Aktualisiere Developer-Workflow in DEVELOPER.md

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 abschliessen.
2. Phase 2 abschliessen.
3. US1 (Phase 3) vollstaendig liefern.
4. US1-Checkpoint validieren.

### Incremental Delivery

1. Setup und Foundation abschliessen.
2. US1 liefern und validieren.
3. US2 liefern und validieren.
4. US3 liefern und validieren.
5. Abschliessend Polish und Gate-Nachweise durchfuehren.

### Parallel Team Strategy

1. Team arbeitet gemeinsam an Phase 1 und 2.
2. Danach parallele Streams:
- Stream A: US1-Migrationspfade.
- Stream B: US2-Importnormalisierung.
- Stream C: US3-Doku und Onboarding.
3. Gemeinsame Abschlussphase mit Gate-Verifikation.
