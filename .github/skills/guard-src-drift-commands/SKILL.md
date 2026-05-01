---
name: guard-src-drift-commands
description: "Drift-generierter Guard fuer `packages/drift-cli` Commands. Aktiv bei Signalen: EDS, PFS. Konfidenz: 0.89. Verwende diesen Skill wenn du Aenderungen an `packages/drift-cli/src/drift_cli/commands` planst oder wiederholte Drift-Findings (EDS, PFS) fuer dieses Modul bearbeitest."
argument-hint: "Beschreibe welchen CLI-Befehl (analyze, verify, serve, calibrate...) du veraenderst und warum."
---

# Guard: `packages/drift-cli/src/drift_cli/commands`

> **ADR-100 Phase 7a:** Kanonischer Code liegt in `packages/drift-cli/src/drift_cli/commands/`.
> `src/drift/commands/` ist ein Re-export-Stub und darf nicht direkt editiert werden.

`packages/drift-cli/src/drift_cli/commands` enthaelt die CLI-Command-Handler. Jeder Subbefehl (`analyze`, `verify`, `serve`, `calibrate`, ...) hat eine eigene Datei. EDS entsteht wenn Commands direkt in `pipeline.py` oder `Analyzer()` einsteigen. PFS entsteht wenn Commands inkonsistente Argument-Parsing- oder Output-Handling-Muster verwenden.

**Konfidenz: 0.89** — EDS und PFS treten regelmaessig auf, oft nach Features die Shortcuts einbauen.

## When To Use

- Du fuegest einen neuen CLI-Subbefehl hinzu
- Du aenderst wie ein bestehender Befehl Argumente verarbeitet oder Ergebnisse ausgibt
- Du aenderst wie Exit-Codes gesetzt werden
- Drift meldet EDS oder PFS fuer eine Datei in `packages/drift-cli/src/drift_cli/commands/`

**Nicht benutzen** fuer Aenderungen an der CLI-Definition in `packages/drift-cli/src/drift_cli/cli.py` — das ist ein anderer Scope.

## Warum dieses Modul kritisch ist

| Signal | Ursache in `commands/` |
|--------|------------------------|
| **EDS** | Command-Handler die direkt `pipeline.run()`, `Analyzer()` oder `scoring/`-Module aufrufen — Command sollte ausschliesslich die entsprechende `api/`-Funktion aufrufen |
| **PFS** | Inkonsistente Exit-Code-Logik: manche Commands nutzen `sys.exit(1)`, andere `raise SystemExit`, andere geben `1` zurueck |

## Core Rules

1. **Commands delegieren an `api/`** — ein Command-Handler tut folgendes: Argumente lesen → `api.function(...)` aufrufen → Ergebnis mit `output/` rendern → Exit-Code setzen. Kein direkter Aufruf von `pipeline.py` oder `Analyzer()`.

2. **Konsistente Exit-Code-Konvention** — `0` = Erfolg, `1` = Findings ueber Threshold, `2` = Konfigurationsfehler, `3` = interne Fehler. Kein eigenes Exit-Code-Schema in einem neuen Command.

3. **Output-Formatierung nicht im Command-Handler** — der Command-Handler uebergibt das Ergebnis an einen Formatter aus `output/`. Kein `print(json.dumps(...))` direkt im Command.

4. **`--format`-Flag konsistent** — alle Commands die Ausgabe erzeugen, unterstuetzen dasselbe `--format`-Flag mit denselben Werten (`rich`, `json`, `markdown`). PFS steigt wenn ein neuer Command andere Werte einfuehrt.

5. **Fehlerbehandlung uniform** — Commands fangen `DriftError` und schreiben in stderr, nicht stdout. Ein neuer Command der Fehler in stdout schreibt bricht tooling-pipelines.

## Review Checklist

- [ ] Command ruft `api.function()` auf, nicht `pipeline.py` direkt
- [ ] Exit-Code folgt der 0/1/2/3-Konvention
- [ ] Output geht durch Formatter aus `output/`, kein direktes `print`
- [ ] `--format`-Flag hat dieselben Werte wie andere Commands
- [ ] Fehler gehen nach stderr, nicht stdout
- [ ] `drift nudge` zeigt `safe_to_commit: true`
- [ ] Keine neuen EDS/PFS-Findings in `src/drift/commands/`

## References

- [packages/drift-cli/src/drift_cli/cli.py](../../../packages/drift-cli/src/drift_cli/cli.py) — CLI-Einstiegspunkt und Command-Registrierung
- [packages/drift-sdk/src/drift_sdk/api/](../../../packages/drift-sdk/src/drift_sdk/api/) — Alle aufrufbaren API-Funktionen
- [packages/drift-output/src/drift_output/](../../../packages/drift-output/src/drift_output/) — Output-Formatter
- [DEVELOPER.md](../../DEVELOPER.md)
