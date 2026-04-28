# Retrieval Slice — Öffentlicher Slice-Vertrag

**Slice**: `src/drift/retrieval/`
**ADR**: [ADR-099 — Vertical Slice Architecture](../../docs/decisions/ADR-099-vertical-slice-architecture.md)
**Status**: Pilot 1 — Migration

---

## Import-Stabilität

Alle unten aufgeführten Symbole sind **stabil** und werden **nicht breaking** geändert.
Imports über `drift.retrieval` bleiben nach der Migration identisch zu vor der Migration.

```python
# Stabile Import-Pfade nach Migration
from drift.retrieval import (
    # Engine
    RetrievalEngine,
    clear_engine_cache,
    # Corpus
    build_corpus,
    # Index
    BM25Index,
    tokenize,
    # Models
    CorpusManifest,
    FactChunk,
    RetrievalResult,
    SourceEntry,
    # Fact IDs
    MigrationRegistry,
    generate_adr_id,
    generate_audit_id,
    generate_evidence_id,
    generate_policy_id,
    generate_signal_id,
)
```

---

## MCP-Tool-Verträge (SC-008: byte-identisch vor/nach Migration)

### `drift_retrieve`

| Parameter | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `path` | `str` | Ja | Absoluter Pfad zum Repo-Root |
| `query` | `str` | Ja | Suchanfrage (nicht leer) |
| `top_k` | `int` | Nein (Default: 5) | Anzahl Treffer ≥ 1 |
| `kind` | `str \| None` | Nein | Filter: `policy \| roadmap \| adr \| audit \| signal \| evidence` |
| `signal_id` | `str \| None` | Nein | Filter auf spezifisches Signal |

**Rückgabe**: `list[RetrievalResult]` (JSON-serialisiert)

### `drift_cite`

| Parameter | Typ | Pflicht | Beschreibung |
|---|---|---|---|
| `path` | `str` | Ja | Absoluter Pfad zum Repo-Root |
| `fact_id` | `str` | Ja | Stable Fact-ID (z. B. `POLICY#S8.p2`) |

**Rückgabe**: `FactChunk | None` (JSON-serialisiert)

---

## Slice-Grenzen (ADR-099 §4 — Cross-Slice Import-Verbot)

Der Retrieval-Slice darf **nicht** importieren aus:
- `drift.signals.*`
- `drift.scoring.*`
- `drift.ingestion.*`
- `drift.output.*`
- `drift.pipeline`
- `drift.analyzer`
- `drift.commands.*`
- `drift.serve.*`
- Anderen künftigen Slices (`drift.intent.*`, `drift.calibrate.*`)

Erlaubte externe Imports:
- `drift.models.*` (Domain-Models, kein Slice)
- `drift.config.*` (Konfiguration, kein Slice)
- `drift.retrieval.*` (interne Slice-Referenzen, keine Kreuzreferenzen)

**Verifikation** (SC-006):
```bash
# Muss 0 Treffer liefern:
grep -r "from drift\.\(intent\|calibrate\|signals\|scoring\|ingestion\|output\)" \
  src/drift/retrieval/
```

---

## Test-Co-Lokalisierung (ADR-099 §5)

Tests des Slices leben in `src/drift/retrieval/tests/`:

```
src/drift/retrieval/tests/
├── __init__.py          # Leer
├── test_corpus.py       # Corpus-Builder- und Parsing-Tests
├── test_mcp.py          # MCP-Tool-Funktionen (run_retrieve, run_cite)
└── test_search.py       # RetrievalEngine und BM25Index
```

Voraussetzung in `pyproject.toml` (Chore-PR):
```toml
[tool.pytest.ini_options]
testpaths = ["tests", "src/drift"]
```

---

## Backward-Compat-Garantie: `mcp_router_retrieval.py`

Der alte Import-Pfad bleibt über den Re-Export-Shim erhalten:
```python
# src/drift/mcp_router_retrieval.py (temporärer Shim)
from drift.retrieval.mcp import *  # noqa: F401,F403
```

Dieser Shim wird in einem **Folge-PR** entfernt, sobald alle internen Konsumenten
auf `drift.retrieval.mcp` migriert sind. Externe Consumer: keine bekannten.
