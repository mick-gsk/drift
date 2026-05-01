---
name: guard-src-drift
description: "Drift-generierter Guard fuer `packages/drift-engine` (Kern-Analyzer). Aktiv bei Signalen: AVS, EDS, MDS, PFS. Konfidenz: 0.95. Verwende diesen Skill wenn du Aenderungen an `packages/drift-engine` planst oder wiederholte Drift-Findings (AVS, EDS, MDS, PFS) fuer dieses Modul bearbeitest."
argument-hint: "Beschreibe die geplante Aenderung in `packages/drift-engine` — welche Datei, welche Funktion, welcher Zweck."
---

# Guard: `packages/drift-engine` (kanonischer Code, vormals `src/drift`)

> **ADR-100 Phase 7a:** Der kanonische Code liegt in `packages/drift-engine/src/drift_engine/`.
> `src/drift/` ist ein reiner Backward-Compat-Layer (Re-export-Stubs). Aenderungen gehoeren in `packages/drift-engine/`, nie in die Stubs.

`packages/drift-engine/src/drift_engine/` enthaelt `analyzer.py`, `pipeline.py`, `cache.py`, `scoring/`, und alle MCP-Orchestrierungs-Module. Jede Aenderung hier hat breite Auswirkungen auf Scan-Korrektheit, Scoring und Agenten-Verhalten.

**Konfidenz: 0.95** — alle vier Hauptsignale treten wiederholt auf.

## When To Use

- Du aenderst eine Datei in `packages/drift-engine/src/drift_engine/`
- Du bearbeitest `analyzer.py`, `pipeline.py`, `cache.py`, `api_helpers.py`, `task_graph.py` oder `scoring/`
- Ein Drift-Scan meldet AVS, EDS, MDS oder PFS fuer Dateien im Engine-Paket
- Vor einem Commit der `packages/drift-engine/src/drift_engine/__init__.py` oder oeffentliche Exports aendert

**Nicht benutzen** fuer Aenderungen ausschliesslich in `packages/drift-engine/src/drift_engine/signals/`, `packages/drift-sdk/src/drift_sdk/api/` oder `packages/drift-output/` — dafuer gibt es dedizierte Guards.

> Hinweis: `src/drift/` im Repo-Root enthaelt nur Re-export-Stubs (ADR-100). Dort nichts aendern.

## Warum dieses Modul kritisch ist

`src/drift/` ist das einzige Modul mit allen vier Hochrisiko-Signalen gleichzeitig:

| Signal | Was es bedeutet | Konkretes Risiko hier |
|--------|-----------------|----------------------|
| **AVS** | God-Module / Abstraction Violation | `analyzer.py` baut Verantwortlichkeiten auf — neue Logik dort zieht AVS an |
| **EDS** | Unexplained Complexity | `drift_map`, `pipeline.py` haben bereits EDS — neue verschraenkte Logik verschlimmert das |
| **MDS** | Exakte Duplikate | Hilfsfunktionen entstehen oft doppelt wenn man nicht `_utils.py` oder `api_helpers.py` nutzt |
| **PFS** | Pattern Fragmentation | MCP-Handler (`mcp_*.py`) haben schon inkonsistente Muster — neue Varianten erhoehen PFS |

## Core Rules

1. **Keine neue Logik direkt in `analyzer.py` oder `pipeline.py`** — diese Dateien sind bereits God-Module-Kandidaten (AVS). Neue Faehigkeiten gehoeren in dedizierte Untermodule oder Klassen.

2. **Duplikate aktiv vermeiden** — vor dem Schreiben einer neuen Hilfsfunktion `grep_search` in `_utils.py`, `api_helpers.py`, `scoring/` und `task_graph.py` laufen lassen. MDS entsteht fast immer dadurch, dass eine existierende Funktion nicht gefunden wurde.

3. **MCP-Handler konsistent halten** — `mcp_router_*.py`-Dateien folgen demselben Muster. Neue Handler muessen dasselbe Routing-Interface implementieren, sonst steigt PFS.

4. **`cache.py` nicht fuer neue Concerns erweitern** — `cache.py` hat bereits hohe DCA (unused exports). Neue Cache-Logik kommt als separate Klasse, nicht als weitere Methode in `BaselineManager`.

5. **Oeffentliche API-Exports explizit halten** — was in `__init__.py` landet, ist Vertrag. Kein implizites Re-Export von internen Symbolen.

## Arbeitsablauf vor einem Commit

```bash
# 1. Scan auf Ziel-Scope
drift analyze --repo . --format rich --exit-zero

# 2. Schnelle Richtungspruefung nach Aenderung
drift nudge  # erwartet: safe_to_commit: true

# 3. Keine neuen AVS/EDS/MDS/PFS einfuehren
# Vergleiche Finding-Count vorher vs. nachher
```

## Review Checklist

- [ ] Neue Logik geht in ein Unterpaket, nicht in `analyzer.py` oder `pipeline.py`
- [ ] Vor neuer Hilfsfunktion: Duplikat-Check in `_utils.py`, `api_helpers.py`, `scoring/`
- [ ] MCP-Handler folgt dem bestehenden `mcp_router_*.py`-Muster
- [ ] `drift nudge` zeigt `safe_to_commit: true`
- [ ] `__init__.py`-Exports sind bewusste, dokumentierte Entscheidungen
- [ ] Keine neuen AVS/EDS/MDS/PFS-Findings im Diff

## References

- [DEVELOPER.md](../../DEVELOPER.md)
- [packages/drift-engine/src/drift_engine/pipeline.py](../../../packages/drift-engine/src/drift_engine/pipeline.py) — Analyse-Pipeline
- [packages/drift-engine/src/drift_engine/analyzer.py](../../../packages/drift-engine/src/drift_engine/analyzer.py) — Haupt-Analyzer
- [packages/drift-sdk/src/drift_sdk/](../../../packages/drift-sdk/src/drift_sdk/) — SDK inkl. api_helpers und types
