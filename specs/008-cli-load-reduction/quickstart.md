# Quickstart: CLI Load Reduction

## Purpose
Diese Anleitung validiert die implementierte Help-Navigation im `packages/drift-cli`-Pfad.

## 1. Projekt vorbereiten
```powershell
pip install -e '.[dev]'
```

## 2. Feature-Tests ausfuehren (T035)
```powershell
.venv\Scripts\python.exe -m pytest tests/help_nav -q --tb=short
.venv\Scripts\python.exe -m pytest tests/test_cli_runtime.py -q --tb=short
```
Ergebnis in dieser Implementierung:
- `tests/help_nav`: 8 passed
- `tests/test_cli_runtime.py`: 18 passed

## 3. CLI-Vertrag pruefen (Root Help + Subcommand)
```powershell
.venv\Scripts\python.exe -m drift --help
.venv\Scripts\python.exe -m drift help-nav
.venv\Scripts\python.exe -m drift help-nav --area investigation
```
Erwartung:
- Sichtbarer `Start Here (80% Path)`-Block als erste Sektion
- Stabile Sektionen: `Investigation`, `Agent & MCP`, `CI & Automation`, `Configuration`, `Measurement`
- Additiver Navigationspfad ueber `help-nav`

## 4. Legacy-Kompatibilitaet stichprobenartig pruefen
```powershell
.venv\Scripts\python.exe -m drift status --help
.venv\Scripts\python.exe -m drift analyze --help
.venv\Scripts\python.exe -m drift scan --help
.venv\Scripts\python.exe -m drift diff --help
```
Erwartung:
- Bestehende Kommandos bleiben aufrufbar
- Keine Umbenennung/Entfernung durch die Orientierungsschicht

## 5. SC-Messprotokolle

### SC-001 Findability (T040)
- Probe: 10 Erstnutzer-Szenarien, jeweils Start bei `drift --help`
- Erfolgsregel: pass, wenn >= 85% in <= 60s den ersten Analysebefehl identifizieren
- Messartefakt: Zeit je Durchlauf + Zielbefehl

### SC-002 Time-to-first-analysis (T038, T039)
- Baseline-Protokoll (vorher): Zeit von erstem `drift --help` bis erstem erfolgreichen `drift analyze --repo .`
- Post-Change-Protokoll (nachher): identische Messmethode
- Erfolgsregel: pass bei mindestens 40% Reduktion gegen Baseline

### SC-004 Clarity-Rating (T041)
- Probe: Nutzerfeedback auf 5er-Skala (`sehr unklar` bis `sehr klar`)
- Erfolgsregel: pass, wenn >= 80% `klar` oder `sehr klar` bewerten

## 6. Repo-weite Pflichtchecks vor Abschluss
```powershell
pre-commit run --all-files
make check
make gate-check COMMIT_TYPE=feat
```

## Done-Kriterien
- SC-001 bis SC-004 sind mit testbaren Protokollen abgedeckt
- Keine Breaking Changes fuer bestehende Befehlspfade
- Help-Navigation ist additiv, stabil und aufgabenorientiert