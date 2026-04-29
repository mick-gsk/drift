# Feature Specification: VSA-Pilot 1 — Migration `retrieval` → Slice-Konvention (ADR-099)

**Feature Branch**: `003-vsa-pilot1-retrieval`
**Created**: 2026-04-28
**Status**: Draft
**ADR**: [ADR-099](../../docs/decisions/ADR-099-vertical-slice-architecture-convention.md)
**Boundary Audit**: [work_artifacts/vsa_pilot1_retrieval_boundary_audit.md](../../work_artifacts/vsa_pilot1_retrieval_boundary_audit.md)
**Test-Strategie**: [work_artifacts/vsa_test_colocation_strategy.md](../../work_artifacts/vsa_test_colocation_strategy.md)

---

## Clarifications

### Session 2026-04-28

- Q: Welche Variante für den MCP-Router-Kanal: Option A (Move + Re-Export-Shim) oder Option B (In-Place-Delegation)? → A: Option A — `mcp_router_retrieval.py` wird nach `src/drift/retrieval/mcp.py` verschoben; am alten Pfad verbleibt ein dünner Re-Export-Shim.
- Q: Wie wird mit `models.py` vs. `contracts.py` im Slice umgegangen? → A: Option C — beide Dateien koexistieren: `contracts.py` für neue Slice-DTOs/Verträge, `models.py` für bestehende Domain-Models. Keine Umbenennung, keine Konsolidierung im Pilot-PR.
- Q: Muss der Chore-PR (testpaths + codecov) vor dem Pilot-PR gemergt sein? → A: Option A — Chore-PR zuerst mergen; saubere Reihenfolge, CI bleibt zu jedem Zeitpunkt grün.
- Q: Wie granular soll `handlers.py` implementiert werden? → A: Option B — Konsolidierung: Use-Case-Logik aus `search.py` und `corpus_builder.py` wird nach `handlers.py` gezogen; die alten Module werden zu internen Hilfsdateien.
- Q: Welche Symbole soll `__init__.py` re-exportieren? → A: Option B — alle aktuell public genutzten Symbole aus `search.py`, `corpus_builder.py`, `index.py` werden in `__all__` aufgenommen (breite, vollständige Surface).

---

## User Scenarios & Testing

### User Story 1 — Slice-Layout herstellen (Priority: P1)

Als Drift-Maintainer möchte ich, dass `src/drift/retrieval/` alle Pflicht-Dateien der
ADR-099-Slice-Konvention enthält (`contracts.py`, `handlers.py`, `mcp.py`), damit der
Use-Case vollständig self-contained und nach ADR-099 konform ist.

**Why this priority**: Ohne das korrekte Slice-Layout existiert der Pilot nur auf dem
Papier; alle anderen Stories bauen auf diesem Fundament auf.

**Independent Test**: Dateisystem-Audit via `file_search` auf
`src/drift/retrieval/{contracts,handlers,mcp}.py` + `grep_search` auf Cross-Slice-Imports.

**Acceptance Scenarios**:

1. **Given** der aktuelle Stand von `src/drift/retrieval/`, **When** der Pilot-PR
   gemergt ist, **Then** enthält das Verzeichnis `contracts.py`, `handlers.py` und
   `mcp.py` (und behält `__init__.py`, `cache.py`, `corpus_builder.py`, `fact_ids.py`,
   `index.py`, `models.py`, `search.py` erhalten oder konsolidiert).
2. **Given** `src/drift/retrieval/`, **When** `grep_search` auf
   `from drift\.(retrieval|intent|calibrate|signals|scoring)` innerhalb des Slices
   ausgeführt wird, **Then** findet sich kein Import aus einem anderen Slice (nur
   Domain-Core und Standard-Bibliothek zulässig).
3. **Given** `src/drift/retrieval/__init__.py`, **When** geöffnet, **Then** exportiert
   es ausschließlich Public-Slice-API-Symbole; keine re-exports fremder Slices.

---

### User Story 2 — MCP-Router-Kanal integrieren (Priority: P1)

Als MCP-Server-Nutzer möchte ich, dass `drift_retrieve`, `drift_cite` und alle weiteren
Retrieval-MCP-Tools nach der Migration unverändert funktionieren (identische Schemas,
identisches Verhalten), egal ob `mcp_router_retrieval.py` verschoben oder in-place
belassen wurde.

**Why this priority**: MCP-Tool-Schema-Brüche wären unmittelbar nutzerseitig sichtbar;
dieses Risiko muss zuerst gesichert sein.

**Independent Test**: `pytest tests/test_mcp_retrieval_tools.py` (oder nach Migration:
`pytest src/drift/retrieval/tests/test_mcp.py`) liefert grünes Ergebnis ohne Patch der
Testinhalte.

**Acceptance Scenarios**:

1. **Given** einer der zwei MCP-Varianten (Option A oder B, siehe Anforderungen), **When**
   der MCP-Server die Tool-Liste zurückgibt, **Then** sind Signatur, Parameter-Namen und
   Beschreibungen der Retrieval-Tools identisch zum Pre-Migration-Stand.
2. **Given** Option A (Move + Shim), **When** `from drift.mcp_router_retrieval import ...`
   in einem externen Skript ausgeführt wird, **Then** funktioniert der Import weiterhin
   über den Re-Export-Shim.
3. **Given** Option B (In-Place), **When** `mcp_router_retrieval.py` unverändert bleibt,
   **Then** importiert es seine Logik aus `src/drift/retrieval/mcp.py` (Delegation) statt
   direkt die Retrieval-Logik zu implementieren.

---

### User Story 3 — Tests co-lokalisieren (Priority: P2)

Als Maintainer möchte ich, dass die drei Retrieval-Test-Dateien gemäß Option C
(Hybrid-Strategie) aus `tests/` nach `src/drift/retrieval/tests/` verschoben werden,
damit Tests mit ihrem Slice reisen und Slice-Self-Containment vollständig ist.

**Why this priority**: Test-Migration ist funktional unabhängig vom Layout, muss aber
koordiniert mit den Pytest- und Codecov-Konfigurationsvoraussetzungen erfolgen.

**Independent Test**: `pytest src/drift/retrieval/tests/` grün ohne inhaltliche Änderung
der Test-Logik; `tests/test_retrieval_corpus.py` etc. existieren danach nicht mehr.

**Acceptance Scenarios**:

1. **Given** `pyproject.toml` wurde um `"src/drift"` in `testpaths` erweitert (separate
   Chore-PR-Voraussetzung), **When** die drei Test-Dateien nach
   `src/drift/retrieval/tests/` verschoben wurden, **Then** findet `pytest` sie automatisch
   via Discovery.
2. **Given** `tests/test_retrieval_corpus.py`, `tests/test_retrieval_search.py`,
   `tests/test_mcp_retrieval_tools.py`, **When** sie nach `src/drift/retrieval/tests/`
   als `test_corpus.py`, `test_search.py`, `test_mcp.py` verschoben werden, **Then**
   enthalten sie denselben Testcode; nur Datei-Pfade ändern sich.
3. **Given** der Pilot-PR, **When** `pytest tests/test_retrieval_corpus.py` ausgeführt
   wird, **Then** schlägt der Test fehl (Datei existiert nicht mehr) — das ist erwartetes
   Verhalten; Discovey läuft über den neuen Pfad.

---

### User Story 4 — Öffentliche Import-Garantie aufrechterhalten (Priority: P1)

Als Nutzer der öffentlichen Drift-API möchte ich, dass
`from drift.retrieval.search import RetrievalEngine` nach der Migration weiterhin
funktioniert, damit externe Skripte und Integrationen nicht brechen.

**Why this priority**: Import-Breakage ist ein sofortiger Bruch der Public-API-Garantie.

**Independent Test**: Python-One-Liner `python -c "from drift.retrieval.search import RetrievalEngine; print('ok')"` schlägt nicht fehl.

**Acceptance Scenarios**:

1. **Given** der aktuelle Import-Pfad `drift.retrieval.search.RetrievalEngine`, **When**
   `handlers.py` oder andere Slice-Dateien angelegt wurden, **Then** bleibt `search.py`
   in `src/drift/retrieval/` erhalten oder `__init__.py` exportiert `RetrievalEngine`
   explizit.
2. **Given** keine Breaking-Changes, **When** `make check` ausgeführt wird, **Then**
   schlägt kein Mypy-Typecheck-Fehler auf dem Import-Pfad auf.

---

### Edge Cases

- Was passiert, wenn `mcp_router_retrieval.py` Circular-Import-Risiken durch einen
  Shim-Re-Export erzeugt? → Circular-Import-Prüfung per `python -c "import drift"` im PR.
- Was passiert, wenn `pyproject.toml`-Vorbedingung (testpaths) noch nicht gemergt ist?
  → Test-Migration als separater Schritt, der explizit auf den Chore-PR wartet; Pilot-PR
  darf die Test-Bewegung weglassen und als `# TODO(vsa-pilot1): move tests` kommentieren.
- Was passiert, wenn `contracts.py` mit bestehendem `models.py` im Slice kollidiert?
  → `models.py` ist Kandidat für Umbenennung zu `contracts.py` oder für explizite Prüfung,
  ob DTOs vs. Domain-Models klar getrennt sind; Entscheidung im PR-Review.

---

## Requirements

### Functional Requirements

- **FR-001**: `src/drift/retrieval/` MUSS nach der Migration `contracts.py` enthalten —
  neue Slice-DTOs und Verträge. Das bestehende `models.py` bleibt unverändert erhalten
  (Domain-Models); keine Umbenennung oder Konsolidierung im Pilot-PR (Option C).
- **FR-002**: `src/drift/retrieval/` MUSS `handlers.py` enthalten — konsolidierte
  Use-Case-Logik für Retrieval. Logik aus `search.py` und `corpus_builder.py` wird nach
  `handlers.py` gezogen; diese Module werden danach zu internen Hilfsdateien (Option B).
- **FR-003**: `src/drift/retrieval/` MUSS `mcp.py` enthalten — MCP-Router-Funktionen
  (entspricht heutigem `mcp_router_retrieval.py`). **Entschieden: Option A** — Move nach
  `src/drift/retrieval/mcp.py` mit Re-Export-Shim am alten Pfad (siehe Clarifications).
- **FR-004**: `src/drift/retrieval/__init__.py` MUSS alle aktuell public genutzten Symbole
  aus `search.py`, `corpus_builder.py` und `index.py` via `__all__` re-exportieren
  (Option B). `RetrievalEngine` MUSS weiterhin über `drift.retrieval.search.RetrievalEngine`
  importierbar bleiben.
- **FR-005**: Keine Cross-Slice-Imports DÜRFEN in `src/drift/retrieval/**` eingeführt
  werden. Zulässig sind nur Imports aus Domain Core (`signals/`, `scoring/`, `models/`,
  `output/`, `pipeline.py`) und Shared Infrastructure (`config/`, `errors/`, `telemetry.py`,
  `cache.py`, `types.py`, `signal_registry.py`).
- **FR-006**: MCP-Tool-Schemas MÜSSEN nach der Migration identisch zum Pre-Migration-Stand
  sein (Signatur, Parameter, Beschreibungen).
- **FR-007**: `pytest tests/test_retrieval_corpus.py tests/test_retrieval_search.py tests/test_mcp_retrieval_tools.py`
  (alte Pfade) ODER `pytest src/drift/retrieval/tests/` (neue Pfade, falls Test-Migration
  erfolgt) MUSS grün sein, ohne inhaltliche Änderung der Tests.
- **FR-008**: `make check` MUSS grün sein (lint, typecheck, full test suite).
- **FR-009**: `make gate-check COMMIT_TYPE=chore` MUSS grün sein.
- **FR-010**: `drift analyze --repo . --format json --exit-zero` DARF gegenüber dem
  Pre-Migration-Baseline keine neuen Findings erzeugen.

### Option A — MCP-Router: Move + Re-Export-Shim ✅ **GEWÄHLT**

- `src/drift/mcp_router_retrieval.py` wird nach `src/drift/retrieval/mcp.py` **verschoben**.
- Am alten Pfad `src/drift/mcp_router_retrieval.py` wird ein **dünner Re-Export-Shim**
  hinterlassen, der alle öffentlichen Symbole re-exportiert. Beispiel:
  ```python
  # Re-export shim — wird in einem Folge-PR entfernt, wenn alle Konsumenten migriert sind
  from drift.retrieval.mcp import *  # noqa: F401,F403
  ```
- **Vorteile**: Slice ist vollständig (inkl. MCP-Kanal); `mcp_router_retrieval.py` folgt
  mittelfristig dem Muster der anderen Router, die ebenfalls in ihre Slices wandern werden.
- **Nachteile**: Shim erhöht kurzfristig die Dateizahl; wildcard-Re-Export kann Mypy
  warnen (lösbar per `__all__` in `mcp.py`).

### Option B — MCP-Router: In-Place-Verbleib mit Delegation ~~(verworfen)~~

- Nicht gewählt. Begründung: Slice wäre nicht vollständig self-contained; widerspricht
  ADR-099. Option A setzt die Konvention vollständig um.

### Test-Migration (Option C — Hybrid)

- **Voraussetzung (separater Chore-PR — muss vor Pilot-PR gemergt sein, Entscheidung Q3)**:
  - `pyproject.toml` → `[tool.pytest.ini_options]` → `testpaths` um `"src/drift"` erweitern.
  - `codecov.yml` → Coverage-Pfade um `src/drift/*/tests/` erweitern.
  - `make check` gegen einen Dummy-Slice-Test validieren, dann Dummy entfernen.
- **Verschiebung in Pilot-PR** (nach gemergtem Chore-PR):

  | Test (alt) | Test (neu) |
  |---|---|
  | `tests/test_retrieval_corpus.py` | `src/drift/retrieval/tests/test_corpus.py` |
  | `tests/test_retrieval_search.py` | `src/drift/retrieval/tests/test_search.py` |
  | `tests/test_mcp_retrieval_tools.py` | `src/drift/retrieval/tests/test_mcp.py` |

- Test-Inhalte bleiben **identisch** — nur Pfade ändern sich.
- `tests/` behält alle Domain-Core-Tests (Signal, Precision/Recall, Pipeline etc.) unberührt.

### Key Entities

- **Slice `retrieval/`**: Self-contained Use-Case unter `src/drift/retrieval/` mit
  Kanälen MCP (`mcp.py`), Use-Case-Logik (`handlers.py`) und lokalen Datenverträgen
  (`contracts.py`).
- **`RetrievalEngine`**: Öffentliches Symbol aus `drift.retrieval.search`; bleibt nach
  Migration importierbar.
- **`mcp_router_retrieval.py`**: Wird nach `src/drift/retrieval/mcp.py` verschoben
  (Option A). Am alten Pfad verbleibt ein Re-Export-Shim bis alle Konsumenten migriert sind.
- **Test-Triple**: `test_corpus.py`, `test_search.py`, `test_mcp.py` — vollständige
  Verhaltensbasis des Slices.

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: Alle drei Slice-Pflicht-Dateien (`contracts.py`, `handlers.py`, `mcp.py`)
  existieren unter `src/drift/retrieval/` nach Merge des Pilot-PRs.
- **SC-002**: `pytest` (alte oder neue Test-Pfade je nach Test-Migrations-Stand) läuft durch
  ohne einen einzigen neu fehlgeschlagenen Test gegenüber dem Pre-Migration-Stand.
- **SC-003**: `make check` beendet mit Exit-Code 0.
- **SC-004**: `make gate-check COMMIT_TYPE=chore` beendet mit Exit-Code 0.
- **SC-005**: `drift analyze --repo . --format json --exit-zero` erzeugt keine neuen Findings
  gegenüber dem vor dem PR aufgenommenen Baseline-Snapshot.
- **SC-006**: `grep_search` auf `from drift\.(intent|calibrate|signals|scoring|ingestion|output)` 
  innerhalb `src/drift/retrieval/**` liefert null Treffer.
- **SC-007**: `python -c "from drift.retrieval.search import RetrievalEngine"` beendet
  ohne Fehler.
- **SC-008**: MCP-Tool-Schemas vor und nach Migration sind byte-identisch (verifizierbar
  via `drift serve --list-tools` oder äquivalentem Tool-Catalog-Aufruf).

---

## Assumptions

- `src/drift/retrieval/` enthält heute: `__init__.py`, `cache.py`, `corpus_builder.py`,
  `fact_ids.py`, `index.py`, `models.py`, `search.py` — verifiziert per `list_dir` am
  2026-04-28. Diese Dateien bleiben unverändert erhalten (Migration fügt hinzu, entfernt nichts
  ohne explizite Prüfung).
- `mcp_router_retrieval.py` ist der **einzige** externe Konsument von `drift.retrieval.*`
  (verifiziert per Boundary-Audit). Kein `commands/`-, `api/`- oder anderer Pfad ist betroffen.
- `retrieval/` hat **keinerlei** ausgehende Imports auf andere `drift.*`-Module außerhalb
  des Slices — verifiziert per Boundary-Audit. Keine Entkopplungsarbeit nötig.
- Die Test-Migrations-Voraussetzung (`pyproject.toml` `testpaths`, `codecov.yml`) wird in
  einem **separaten Chore-PR** vor oder parallel zum Pilot-PR geliefert. Pilot-PR ist erst
  dann vollständig, wenn diese Vorbedingung erfüllt ist.
- Pilot 1 löst **keine** POLICY-§18-Audit-Pflicht aus: keine Signale, kein Scoring, keine
  Output-Verträge, keine Trust-Boundaries werden berührt.
- Der Commit-Typ für den Pilot-PR ist `chore:` (kein neues Feature, keine Bug-Fix, reine
  Strukturmigration). Commit-Trailer: `Decision: ADR-099`.
- `models.py` im Slice ist ein Kandidat für Umbenennung zu oder Konsolidierung mit
  `contracts.py`. Die finale Entscheidung (behalten/umbenennen/konsolidieren) wird im PR
  getroffen und muss nicht vorab fixiert werden.

---

## Out of Scope (nicht verhandelbar)

- `src/drift/signals/`, `src/drift/scoring/`, `src/drift/ingestion/`, `src/drift/models/`,
  `src/drift/output/`, `src/drift/pipeline.py`, `src/drift/analyzer.py` — keine Berührung.
- Migration von `intent/` oder `calibrate/` — separate Pilots (Pilot 2 und 3 laut ADR-099).
- Verhaltensänderungen jeglicher Art an bestehenden Retrieval-Funktionen.
- Neue Features, neue Public-API-Symbole, neue MCP-Tools.
- Refactoring innerhalb bestehender Retrieval-Module, das über das Slice-Layout hinausgeht.
- Anpassung der Audit-Artefakte (`fmea_matrix.md`, `risk_register.md`, `fault_trees.md`,
  `stride_threat_model.md`) — POLICY §18 wird nicht ausgelöst.
