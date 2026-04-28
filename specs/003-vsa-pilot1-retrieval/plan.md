# Implementation Plan: VSA-Pilot 1 — `retrieval` Slice-Migration (ADR-099)

**Branch**: `main` | **Date**: 2026-04-28 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-vsa-pilot1-retrieval/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Migriert `src/drift/retrieval/` zur vollständigen ADR-099-Slice-Konvention:

1. **Chore-PR** (Voraussetzung): `testpaths` in `pyproject.toml` und `codecov.yml` erweitern,
   damit Slice-Tests in `src/drift/retrieval/tests/` von CI und Coverage erkannt werden.
2. **Pilot-PR** (Hauptarbeit):
   - `contracts.py` anlegen (Pflicht-Datei, initial minimal)
   - `handlers.py` anlegen (Use-Case-Konsolidierung aus `search.py` + `corpus_builder.py`)
   - `mcp_router_retrieval.py` → `retrieval/mcp.py` verschieben + Re-Export-Shim am alten Pfad
   - `__init__.py` mit breitem `__all__` aktualisieren (alle public Symbole)
   - Tests von `tests/` → `src/drift/retrieval/tests/` verschieben

Kein Verhaltensunterschied; alle SC-001–SC-008 müssen grün sein.
Commit-Typ: `chore:` mit Trailer `Decision: ADR-099`.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: Pydantic (frozen models), FastMCP (MCP-Server), Click, Rich, pytest, uv, mypy, ruff
**Storage**: File-System (Corpus-Cache via `drift.retrieval.cache`; BM25-Index in-memory)
**Testing**: pytest + pytest-xdist; bestehende Tests werden verschoben, kein neuer Test-Framework
**Target Platform**: Python-Package (PyPI); Linux + Windows (CI + lokale Entwicklung)
**Project Type**: Library (interne Slice-Migration — keine neue User-visible CLI/API)
**Performance Goals**: Keine Regression vs. Pre-Migration-Baseline (`benchmark_results/drift_self.json`)
**Constraints**: `make check` gr\u00fcn; `make gate-check COMMIT_TYPE=chore` gr\u00fcn; SC-001\u2013SC-008; kein Cross-Slice-Import
**Scale/Scope**: ~7 Quelldateien ge\u00e4ndert/angelegt; 3 Test-Dateien verschoben; 1 Shim-Datei ge\u00e4ndert

## Constitution Check

*GATE: Alle f\u00fcnf Prinzipien evaluiert. Constitution v1.0.0.*

- [x] **I. Library-First**: `handlers.py` konsolidiert Use-Case-Logik ausschlie\u00dflich in der Library.
  `mcp.py` ist ein d\u00fcnner Binding-Layer \u2014 keine Gesch\u00e4ftslogik im MCP-Kanal.
  CLI bleibt unangetastet. ✅

- [~] **II. Test-First**: BEGR\u00dcNDETE AUSNAHME \u2014 reine Code-Verschiebung ohne neue Logik.
  Bestehende Tests (`test_retrieval_corpus.py`, `test_retrieval_search.py`, `test_mcp_retrieval_tools.py`)
  werden **ohne Inhalts\u00e4nderungen** in das Slice verschoben und dienen als Regressionssuite.
  Neue Logik in `handlers.py` (thin delegation) wird von diesen Tests bereits abgedeckt.
  FR-007: Tests m\u00fcssen bestehen ohne Inhalts\u00e4nderungen \u2014 das ist die h\u00e4rteste Form von TDD-Evidenz. ⚠️
  **Maintainer-Approval: accepted** (Mick Gottschalk, 2026-04-28 -- per speckit.analyze-Review). ⚠️

- [x] **III. Functional Programming**: Keine neuen ver\u00e4nderlichen Zust\u00e4nde eingef\u00fchrt.
  `FactChunk`, `RetrievalResult`, `CorpusManifest`, `SourceEntry` bleiben frozen Pydantic-Modelle.
  `contracts.py` leer \u2014 kein neuer Zustand. `handlers.py` delegiert auf reine Funktionen. ✅

- [x] **IV. CLI Interface & Observability**: Keine CLI-\u00c4nderungen. MCP-Tool-Schemas bleiben
  byte-identisch (SC-008). `mcp.py` ist direkte Kopie von `mcp_router_retrieval.py`.
  Kein neues CLI-Subcommand \u2014 korrekt, da Migration kein Feature ist. ✅

- [x] **V. Simplicity & YAGNI**: Minimaler Scope. `contracts.py` startet leer (kein Over-Engineering).
  `handlers.py` als d\u00fcnner Delegation-Layer \u2014 einfachste ADR-099-konforme Umsetzung.
  Shim am alten Pfad: 1 Zeile. Keine neuen Abstraktionen ohne konkreten Bedarf. ✅

## Project Structure

### Documentation (this feature)

```text
specs/003-vsa-pilot1-retrieval/
├── plan.md              # Dieses Dokument (/speckit.plan)
├── research.md          # Phase 0: Architekturentscheidungen (/speckit.plan)
├── data-model.md        # Phase 1: Entities und Slice-Layout (/speckit.plan)
├── quickstart.md        # Phase 1: Nutzungsbeispiele (/speckit.plan)
├── contracts/           # Phase 1: \u00d6ffentliche Slice-Vertr\u00e4ge (/speckit.plan)
│   └── retrieval-slice.md
└── tasks.md             # Phase 2: Aufgabenliste (/speckit.tasks \u2014 NICHT von /speckit.plan)
```

### Chore-PR (Voraussetzung \u2014 muss VOR Pilot-PR gemergt sein)

```text
# pyproject.toml [tool.pytest.ini_options]
testpaths = ["tests", "src/drift"]   # +src/drift

# codecov.yml
coverage:
  include:
    - src/drift/*/tests/**           # Neu hinzugef\u00fcgt
```

### Pilot-PR (Haupt\u00e4nderungen)

```text
src/drift/retrieval/
├── __init__.py             # GE\u00c4NDERT: breiter __all__ (RetrievalEngine + build_corpus + BM25Index + tokenize + clear_engine_cache + alle models + alle fact_ids)
├── cache.py                # UNVER\u00c4NDERT
├── contracts.py            # NEU \u2014 Pflicht-Datei ADR-099, initial minimal (nur Docstring + Kommentar)
├── corpus_builder.py       # UNVER\u00c4NDERT (parse_* bleiben internes Hilfsmodul)
├── fact_ids.py             # UNVER\u00c4NDERT
├── handlers.py             # NEU \u2014 Use-Case-Layer: retrieve(), cite(), get_engine(), invalidate_cache()
├── index.py                # UNVER\u00c4NDERT
├── mcp.py                  # NEU \u2014 verschoben aus mcp_router_retrieval.py (run_retrieve, run_cite)
├── models.py               # UNVER\u00c4NDERT
├── search.py               # UNVER\u00c4NDERT (bleibt Implementierungsdetail)
└── tests/                  # NEU (Verzeichnis)
    ├── __init__.py         # NEU (leer)
    ├── test_corpus.py      # VERSCHOBEN aus tests/test_retrieval_corpus.py
    ├── test_mcp.py         # VERSCHOBEN aus tests/test_mcp_retrieval_tools.py
    └── test_search.py      # VERSCHOBEN aus tests/test_retrieval_search.py

src/drift/mcp_router_retrieval.py   # GE\u00c4NDERT: wird zu Re-Export-Shim (1 Zeile)

tests/                              # GE\u00c4NDERT: 3 Dateien gel\u00f6scht (in Slice verschoben)
├── test_retrieval_corpus.py        # ENTFERNT (in Slice verschoben)
├── test_retrieval_search.py        # ENTFERNT (in Slice verschoben)
└── test_mcp_retrieval_tools.py     # ENTFERNT (in Slice verschoben)
```

**Structure Decision**: Option 1 (Single project, Library). Kein Frontend, kein Backend, kein
separater Service. Alle \u00c4nderungen innerhalb `src/drift/retrieval/`. Tests co-lokalisiert im Slice.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| Constitution II (Test-First) | Reine Code-Verschiebung ohne neue Logik | Tests schreiben f\u00fcr identisches Verhalten w\u00e4re Overhead ohne Sicherheitswert; FR-007 verlangt explizit Tests-ohne-\u00c4nderung |

