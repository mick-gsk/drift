---
name: guard-src-drift-ingestion
description: "Drift-generierter Guard fuer `src/drift/ingestion`. Aktiv bei Signalen: AVS, EDS, PFS. Konfidenz: 0.95. Verwende diesen Skill wenn du Aenderungen an `src/drift/ingestion` planst oder wiederholte Drift-Findings (AVS, EDS, PFS) fuer dieses Modul bearbeitest."
argument-hint: "Beschreibe die geplante Aenderung in `src/drift/ingestion` — welche Pipeline-Stufe, welches Format (Python/TypeScript/Git)."
---

# Guard: `src/drift/ingestion`

`src/drift/ingestion` ist die Datenerfassungsschicht: `file_discovery.py` findet Dateien, `ast_parser.py` und `ts_parser.py` parsen Code, `git_history.py` und `git_blame.py` lesen Commit-Historie, `external_report.py` importiert SARIF/externe Reports. Jede Datei hat eine klar abgegrenzte Aufgabe — AVS, EDS und PFS entstehen wenn diese Grenzen verschwimmen.

**Konfidenz: 0.95** — Ingestion-Fehler propagieren still und erzeugen falsche Negatives in jedem Signal.

## When To Use

- Du aenderst wie Dateien gefunden, gefiltert oder gelesen werden (`file_discovery.py`)
- Du erweiterst den AST-Parser fuer neue Python-Konstrukte oder Tree-sitter-Nodes
- Du veraenderst wie Git-Commits oder Blame-Daten eingelesen werden
- Du fuegest Unterstuetzung fuer ein neues Sprachformat hinzu
- Drift meldet AVS, EDS oder PFS fuer Dateien in `packages/drift-engine/src/drift_engine/ingestion/`

## Warum dieses Modul kritisch ist

| Signal | Ursache in `ingestion/` |
|--------|------------------------|
| **AVS** | `ast_parser.py` zaehlt Aufgaben: parsen + normalisieren + Metadaten extrahieren + Fehlerbehandlung — zu viele Verantwortlichkeiten |
| **EDS** | Git-Commit-Logik und AST-Traversierung teilen sich Zustand oder Helper — erzeugt unverstaendliche Kopplung |
| **PFS** | Python-Parsing und TypeScript-Parsing haben unterschiedliche Fehlerbehandlungs- und Rueckgabemuster |

## Core Rules

1. **Strikte Trennung der Ingestion-Stufen** — Datei-Entdeckung (`file_discovery.py`) darf NICHT parsen. Parser duerfen NICHT Git-History lesen. Jede Ingestion-Stufe erhaelt ihre Daten als Parameter, nicht durch direkten Aufruf einer anderen Stufe.

2. **`ParseResult` ist das einzige Ausgabeformat der Parser** — `ast_parser.py` und `ts_parser.py` geben ausschliesslich `ParseResult`-Objekte zurueck. Kein direktes Schreiben in Dictionaries oder nakedObjects.

3. **Fehler in Parsern sind `ParseResult` mit `error`-Status** — nie `raise` ohne Wrapper in Parsern. Ein fehlerhafter Parse erzeugt ein `ParseResult(status='error', ...)`, kein unbehandeltes Exception.

4. **`FileHistory` bleibt dekoriert, nicht berechnet** — `git_history.py` liest Rohcommits und gibt `FileHistory` zurueck. Keine Berechnungen (Volatility-Score, Hotness) in `git_history.py` — das ist Aufgabe von Signals.

5. **Include/Exclude-Logik gehoert ausschliesslich in `file_discovery.py`** — kein Signal und kein API-Handler darf Dateipfade selbst filtern. PFS entsteht wenn mehrere Stellen eigene Include-Logik haben.

## Iron Law

> **Kein neues Dateiformat ohne Test in `tests/test_file_discovery.py`.** Stummes Ueberspringen von `.pyi`, `.mjs`, `.mts`-Dateien war bereits eine Regression — reproducierbare Tests verhindern das.

## Review Checklist

- [ ] Neue Parser-Logik gibt `ParseResult` zurueck, kein Dict oder tuple
- [ ] Fehlerfall in Parsern: `ParseResult(status='error')`, kein `raise`
- [ ] `file_discovery.py` ist einzige Stelle fuer Include/Exclude-Logik
- [ ] Git-History-Funktionen berechnen keine Scores (nur rohe `FileHistory`)
- [ ] Tests in `tests/test_file_discovery.py` abgedeckt
- [ ] `drift nudge` zeigt `safe_to_commit: true`
- [ ] Keine neuen AVS/EDS/PFS-Findings

## References

- [packages/drift-engine/src/drift_engine/ingestion/file_discovery.py](../../../packages/drift-engine/src/drift_engine/ingestion/file_discovery.py) — Discovery-Pipeline
- [packages/drift-engine/src/drift_engine/ingestion/ast_parser.py](../../../packages/drift-engine/src/drift_engine/ingestion/ast_parser.py) — Python-AST-Parser
- [packages/drift-engine/src/drift_engine/ingestion/git_history.py](../../../packages/drift-engine/src/drift_engine/ingestion/git_history.py) — Git-History-Reader
- [tests/test_file_discovery.py](../../../tests/test_file_discovery.py) — Discovery-Tests
