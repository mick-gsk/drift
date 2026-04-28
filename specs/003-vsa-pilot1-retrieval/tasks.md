# Tasks: VSA-Pilot 1 — `retrieval` Slice-Migration (ADR-099)

**Input**: Design documents from `specs/003-vsa-pilot1-retrieval/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Kann parallel ausgeführt werden (verschiedene Dateien, keine unerfüllten Abhängigkeiten)
- **[US1]–[US4]**: User-Story-Zugehörigkeit (aus spec.md)
- Alle Pfade sind Workspace-relativ

---

## Phase 1: Setup — Chore-PR-Voraussetzung

**Zweck**: CI-Infrastruktur für Test-Co-Lokalisierung vorbereiten.
Dieser Chore-PR muss **vor dem Pilot-PR gemergt** sein.

**Checkpoint**: `pytest src/drift/retrieval/tests/` wird von pytest-discovery erkannt.

- [X] T001 Erweitere `pyproject.toml` → `[tool.pytest.ini_options]` → `testpaths` um `"src/drift"` in `pyproject.toml`
- [X] T002 Erweitere `codecov.yml` → Coverage-Pfade um `src/drift/*/tests/**` in `codecov.yml`
- [X] T003 Validiere Chore-PR: erzeuge `src/drift/retrieval/tests/__init__.py` und `src/drift/retrieval/tests/_smoke.py` (Dummy-Test `assert True`), führe `make check` aus, dann lösche Dummy-Dateien wieder. *Falls `make check` fehlschlägt: Dummy-Dateien sofort löschen, Konfiguration korrigieren, erneut durchlaufen.*
- [X] T004 Erstelle Chore-PR-Commit: `chore: extend testpaths and codecov for slice test co-location` mit Trailer `Decision: ADR-099`

---

## Phase 2: Foundational — Slice-Verzeichnis-Skeleton

**Zweck**: Pflicht-Dateien nach ADR-099 anlegen, bevor User-Story-spezifischer Code folgt.
Alle User Stories bauen auf diesem Skeleton auf.

**⚠️ KRITISCH**: Keine User-Story-Arbeit beginnt, bis Phase 2 abgeschlossen ist.

**Checkpoint**: `src/drift/retrieval/` enthält `contracts.py`, `handlers.py`, `mcp.py` und `tests/__init__.py`; `python -c "import drift.retrieval"` läuft fehlerfrei.

- [X] T005 Erstelle `src/drift/retrieval/tests/__init__.py` (leer) in `src/drift/retrieval/tests/__init__.py` *(In Phase 1/Chore-PR temporär erstellt und gelöscht — hier die permanente Erstellung für den Pilot-PR)*
- [X] T006 [P] Erstelle `src/drift/retrieval/contracts.py` (minimal: Modul-Docstring + `# Initial leer — Pflicht-Datei ADR-099`) in `src/drift/retrieval/contracts.py`
- [X] T007 [P] Erstelle `src/drift/retrieval/handlers.py`-Skeleton (Modul-Docstring, Imports von `search` und `corpus_builder`, Funktions-Stubs `retrieve`, `cite`, `get_engine`, `invalidate_cache` mit `raise NotImplementedError`) in `src/drift/retrieval/handlers.py`
- [X] T008 Verifiziere: `python -c "from drift.retrieval import contracts, handlers"` schlägt nicht fehl (Modul importierbar, auch wenn Stubs noch `NotImplementedError` werfen)

---

## Phase 3: User Story 1 — Slice-Layout herstellen (Priority: P1) 🎯 MVP

**Goal**: `src/drift/retrieval/` enthält alle drei ADR-099-Pflicht-Dateien mit realem Inhalt;
Cross-Slice-Import-Freiheit verifiziert; `__init__.py` exportiert breiten `__all__`.

**Independent Test**:
```bash
python -c "from drift.retrieval.search import RetrievalEngine; print('SC-007 ok')"
grep -rn "from drift\.\(intent\|calibrate\|signals\|scoring\|ingestion\|output\)" src/drift/retrieval/ && echo "FAIL" || echo "SC-006 ok"
```

### Implementation für US1

- [X] T009 [US1] Implementiere `src/drift/retrieval/handlers.py` — ersetze Stubs durch dünne Delegationen auf `search.py` und `corpus_builder.py`: `retrieve()` delegiert auf `RetrievalEngine.retrieve()`, `cite()` auf `RetrievalEngine.cite()`, `get_engine()` auf `RetrievalEngine.for_repo()`, `invalidate_cache()` auf `clear_engine_cache()` in `src/drift/retrieval/handlers.py`
- [X] T010 [P] [US1] Aktualisiere `src/drift/retrieval/__init__.py`: füge breiten `__all__` ein mit allen Symbolen aus `fact_ids`, `models`, `search` (RetrievalEngine, clear_engine_cache), `corpus_builder` (build_corpus), `index` (BM25Index, tokenize) in `src/drift/retrieval/__init__.py`
- [X] T011 [P] [US1] Verifiziere Cross-Slice-Import-Freiheit: führe `grep -rn "from drift\.\(intent\|calibrate\|signals\|scoring\|ingestion\|output\)" src/drift/retrieval/` aus — muss 0 Treffer liefern (SC-006)
- [X] T012 [US1] Verifiziere Public-Import-Stabilität: `python -c "from drift.retrieval.search import RetrievalEngine; print('ok')"` — muss funktionieren (SC-007)
- [X] T013 [US1] Verifiziere breite `__init__`-Surface: `python -c "from drift.retrieval import RetrievalEngine, build_corpus, BM25Index, tokenize, clear_engine_cache, FactChunk, RetrievalResult; print('all ok')"` — muss ohne Fehler durchlaufen *(FactChunk/RetrievalResult sind via models.py bereits öffentlich — vorab verifiziert 2026-04-28)*

**Checkpoint**: US1 abgeschlossen — Slice-Layout komplett, Import-Garantien grün, Cross-Slice-Check sauber.

---

## Phase 4: User Story 2 — MCP-Router-Kanal integrieren (Priority: P1)

**Goal**: `mcp_router_retrieval.py` → `src/drift/retrieval/mcp.py` verschoben;
Re-Export-Shim am alten Pfad; MCP-Tool-Schemas unverändert.

**Independent Test**:
```bash
python -c "from drift.retrieval.mcp import run_retrieve, run_cite; print('mcp.py ok')"
python -c "from drift.mcp_router_retrieval import run_retrieve, run_cite; print('shim ok')"
```

### Implementation für US2

- [X] T014a [US2] Erstelle Pre-Migration-MCP-Schema-Snapshot: `python -m drift mcp --schema > work_artifacts/mcp_schema_pre.json` — wird in T032 als Baseline verwendet (SC-008)
- [X] T014 [US2] Erstelle `src/drift/retrieval/mcp.py` als vollständige Kopie von `src/drift/mcp_router_retrieval.py` (exakter Inhalt — kein Edit nötig, Imports sind bereits korrekt). Verifiziere danach: `python -c "import drift.retrieval.mcp"` in `src/drift/retrieval/mcp.py`
- [X] T015 [US2] Ersetze Inhalt von `src/drift/mcp_router_retrieval.py` durch Re-Export-Shim: `from drift.retrieval.mcp import *  # noqa: F401,F403` + Docstring-Kommentar in `src/drift/mcp_router_retrieval.py`
- [X] T016 [US2] Verifiziere: `python -c "from drift.retrieval.mcp import run_retrieve, run_cite; print('ok')"` — neuer Pfad funktioniert
- [X] T017 [US2] Verifiziere Shim: `python -c "from drift.mcp_router_retrieval import run_retrieve, run_cite; print('shim ok')"` — alter Pfad funktioniert via Shim
- [X] T018 [P] [US2] Führe bestehende MCP-Tests gegen neuen Pfad aus: `pytest tests/test_mcp_retrieval_tools.py -v` — alle Tests müssen grün sein ohne Inhaltsänderung (FR-007, SC-002)

**Checkpoint**: US2 abgeschlossen — MCP-Kanal im Slice, Shim am alten Pfad, alle MCP-Tests grün.

---

## Phase 5: User Story 3 — Tests co-lokalisieren (Priority: P2)

**Goal**: Drei Test-Dateien von `tests/` → `src/drift/retrieval/tests/` verschoben;
alte Pfade gelöscht; `pytest src/drift/retrieval/tests/` findet und besteht alle Tests.

**Voraussetzung**: Chore-PR (Phase 1) muss gemergt sein (`testpaths` in `pyproject.toml`).

**Independent Test**:
```bash
pytest src/drift/retrieval/tests/ -v --tb=short
```

### Implementation für US3

- [X] T019 [US3] Verschiebe `tests/test_retrieval_corpus.py` → `src/drift/retrieval/tests/test_corpus.py` (exakter Inhalt, keine Inhaltsänderung) in `src/drift/retrieval/tests/test_corpus.py`
- [X] T020 [P] [US3] Verschiebe `tests/test_retrieval_search.py` → `src/drift/retrieval/tests/test_search.py` (exakter Inhalt, keine Inhaltsänderung) in `src/drift/retrieval/tests/test_search.py`
- [X] T021 [P] [US3] Verschiebe `tests/test_mcp_retrieval_tools.py` → `src/drift/retrieval/tests/test_mcp.py` (exakter Inhalt, keine Inhaltsänderung) in `src/drift/retrieval/tests/test_mcp.py`
- [X] T022 [US3] Lösche alte Test-Dateien: `tests/test_retrieval_corpus.py`, `tests/test_retrieval_search.py`, `tests/test_mcp_retrieval_tools.py`
- [X] T023 [US3] Verifiziere Test-Discovery: `pytest src/drift/retrieval/tests/ -v` — alle verschobenen Tests werden gefunden und sind grün (SC-002)
- [X] T024 [P] [US3] Verifiziere, dass alte Pfade nicht mehr existieren: `python -c "import os; assert not os.path.exists('tests/test_retrieval_corpus.py'), 'Alter Pfad noch vorhanden'"` und analog für search/mcp

**Checkpoint**: US3 abgeschlossen — Tests leben im Slice, Discovery grün, alte Pfade bereinigt.

---

## Phase 6: User Story 4 — Öffentliche Import-Garantie aufrechterhalten (Priority: P1)

**Goal**: Alle bestehenden Import-Pfade funktionieren nach der Migration;
Mypy findet keine Typ-Fehler; `make check` ist grün.

**Independent Test**:
```bash
python -c "from drift.retrieval.search import RetrievalEngine; print('ok')"
make check
```

### Implementation für US4

- [X] T025 [US4] Früh-Warnung Mypy (Slice-Only): `mypy src/drift/retrieval/ --strict` — kein Fehler; falls Shim-Wildcard Mypy-Warnungen erzeugt, füge `__all__` in `mcp.py` ein *(T025 = Early-Warning für den Slice; T026 = vollständiges `make check` für den gesamten Workspace)*
- [X] T026 [P] [US4] Führe `make check` aus — Exit-Code 0 (SC-003, FR-008)
- [X] T027 [P] [US4] Führe `make gate-check COMMIT_TYPE=chore` aus — Exit-Code 0 (SC-004, FR-009)
- [X] T028 [US4] Führe Drift-Selbstanalyse durch: `drift analyze --repo . --format json --exit-zero` — keine neuen Findings gegenüber Baseline (SC-005, FR-010)

**Checkpoint**: US4 abgeschlossen — alle Import-Garantien grün, Mypy sauber, `make check` und `gate-check` bestehen.

---

## Phase 7: Polish & Abschluss

**Zweck**: Finale Verifikation aller SC-001–SC-008, Commit vorbereiten.

- [X] T029 Verifiziere SC-001: `python -c "import os; [print(f + ' ok') for f in ['contracts.py','handlers.py','mcp.py'] if os.path.exists(f'src/drift/retrieval/{f}')]"` — alle 3 Dateien vorhanden
- [X] T030 [P] Verifiziere SC-007: `python -c "from drift.retrieval.search import RetrievalEngine; print('SC-007 ok')"` *(Finales Recheck — T012 in Phase 3 wiederholt, absichtliche Redundanz als Polish-Checkpoint)*
- [X] T031 [P] Verifiziere SC-006: `grep -rn "from drift\.\(intent\|calibrate\|signals\|scoring\|ingestion\|output\)" src/drift/retrieval/` — 0 Treffer *(Finales Recheck — T011 in Phase 3 wiederholt, absichtliche Redundanz als Polish-Checkpoint)*
- [X] T032 Verifiziere SC-008: `python -m drift mcp --schema > work_artifacts/mcp_schema_post.json; Compare-Object (Get-Content work_artifacts/mcp_schema_pre.json) (Get-Content work_artifacts/mcp_schema_post.json)` — Schemas identisch (keine Ausgabe = gleich); Baseline aus T014a
- [X] T033 Erstelle Pilot-PR-Commit: `chore: migrate retrieval to ADR-099 slice convention` mit Trailer `Decision: ADR-099`

---

## Dependencies

```
Phase 1 (Chore-PR) muss gemergt sein → bevor Phase 5 (Test-Migration) beginnen kann

Phase 2 (Foundational Skeleton) →
  Phase 3 (US1: Slice-Layout) →
    Phase 4 (US2: MCP-Kanal) →  unabhängig von Phase 5
    Phase 5 (US3: Test-Migration) → benötigt Phase 1 (Chore-PR) + Phase 2
    Phase 6 (US4: Import-Garantie) → benötigt Phase 3 + Phase 4

Phase 7 (Polish) → benötigt alle vorherigen Phasen
```

### Parallele Ausführung per User Story

**Chore-PR** (T001–T004): Sequenziell, eigener PR-Branch.

**Pilot-PR — Parallel-Start nach Phase 2**:
- US2 (T014–T018) und US3 (T019–T024) können parallel nach Phase 2 beginnen
- US4 (T025–T028) startet erst nach US1 + US2 abgeschlossen

---

## Implementation Strategy

**MVP-Scope** (P1-User-Stories zuerst): Phase 2 → Phase 3 → Phase 4 → Phase 6

US1, US2, US4 sind alle P1 und bilden das vollständige Slice. US3 (Test-Migration, P2) kann
in einem separaten Schritt nachgeliefert werden, sobald der Chore-PR gemergt ist.

**Inkrementelle Lieferung**:
1. Chore-PR committen und mergen (Phase 1)
2. Pilot-PR: Phase 2 + 3 + 4 + 6 (US1, US2, US4)
3. Pilot-PR-Erweiterung oder Folge-PR: Phase 5 (US3, Test-Migration)

---

## Summary

| Metrik | Wert |
|---|---|
| Gesamte Tasks | 34 |
| Phase 1 (Chore-PR Setup) | 4 |
| Phase 2 (Foundational Skeleton) | 4 |
| Phase 3 (US1 — Slice-Layout) | 5 |
| Phase 4 (US2 — MCP-Kanal) | 6 |
| Phase 5 (US3 — Test-Migration) | 6 |
| Phase 6 (US4 — Import-Garantie) | 4 |
| Phase 7 (Polish) | 5 |
| Parallel-Tasks ([P]) | 14 |
| MVP-Scope (P1-Stories) | Phase 2 + 3 + 4 + 6 (18 Tasks) |
