# Quickstart: Retrieval Slice nach VSA-Migration

**Slice**: `src/drift/retrieval/`
**Zielgruppe**: Entwickler, die nach der Pilot-1-Migration Retrieval-Funktionen nutzen.

---

## Imports (unverändert nach Migration)

```python
# Alle bestehenden Imports funktionieren wie bisher:
from drift.retrieval import RetrievalEngine
from drift.retrieval import build_corpus, FactChunk, RetrievalResult

# Alternativ direkt aus dem Slice (äquivalent):
from drift.retrieval.search import RetrievalEngine
from drift.retrieval.corpus_builder import build_corpus
```

---

## Retrieval ausführen

```python
from drift.retrieval import RetrievalEngine

# Engine für ein Repo initialisieren (cached, thread-safe)
engine = RetrievalEngine.for_repo("/path/to/repo")

# Abfragen
results = engine.retrieve(query="pattern fragmentation signal", top_k=5)
for r in results:
    print(r.fact_id, r.score, r.excerpt[:80])
```

---

## Zitieren (cite)

```python
from drift.retrieval import RetrievalEngine

engine = RetrievalEngine.for_repo("/path/to/repo")

# Fact-Chunk direkt abrufen
chunk = engine.cite("POLICY#S8.p2")
if chunk:
    print(chunk.text)
    print(chunk.sha256)  # Verifizierbarer Anker
```

---

## Corpus manuell aufbauen

```python
from drift.retrieval import build_corpus

manifest, chunks = build_corpus("/path/to/repo")
print(f"Corpus: {len(chunks)} Chunks, SHA {manifest.corpus_sha256[:8]}")
```

---

## MCP-Tools verwenden (nach Slice-Migration)

MCP-Tools sind nach der Migration in `drift.retrieval.mcp` verfügbar:

```python
# Neuer Pfad (nach Migration):
from drift.retrieval.mcp import run_retrieve, run_cite

# Alter Pfad (Re-Export-Shim, temporär noch gültig):
from drift.mcp_router_retrieval import run_retrieve, run_cite
```

---

## Tests ausführen (Slice-Tests)

Nach der Chore-PR-Voraussetzung (`testpaths = ["tests", "src/drift"]` in `pyproject.toml`):

```bash
# Alle Slice-Tests:
pytest src/drift/retrieval/tests/ -v

# Einzelne Test-Datei:
pytest src/drift/retrieval/tests/test_search.py -v

# Als Teil von make check (integriert):
make check
```

---

## Cache invalidieren

```python
from drift.retrieval import clear_engine_cache

# Cache für ein spezifisches Repo leeren (z. B. nach Corpus-Änderungen):
clear_engine_cache("/path/to/repo")

# Oder über handlers.py (nach Pilot-PR):
from drift.retrieval.handlers import invalidate_cache
invalidate_cache("/path/to/repo")
```

---

## Fehlerdiagnose

| Symptom | Ursache | Lösung |
|---|---|---|
| `ModuleNotFoundError: drift.retrieval.mcp` | Pilot-PR noch nicht gemergt | Alten Pfad `mcp_router_retrieval` nutzen |
| `pytest` findet keine Slice-Tests | Chore-PR fehlt | `testpaths` in `pyproject.toml` prüfen |
| `SC-007` schlägt fehl | `__init__.py` unvollständig | `__all__` und Imports prüfen |
| `SC-006` schlägt fehl | Unerwünschte Cross-Slice-Imports | `grep -r "from drift\.(signals|scoring|...)"` ausführen |
