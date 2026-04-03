---
name: "Drift Agent Workflow Test"
agent: agent
description: "Testet alle Drift-CLI-Pfade End-to-End: Installation, Analyse, Export, Konfiguration, Edge-Cases, CI-Realism. Strukturierte Testmatrix mit pass/review/fail-Bewertung."
---

# Drift Agent Workflow Test

Vollständiger funktionaler Workflow-Test aller Drift-CLI-Kommandos und Konfigurationspfade. Jeder Pfad wird mit konkretem Input ausgeführt und das Ergebnis dokumentiert.

> **Pflicht:** Vor Ausführung dieses Prompts das Drift Policy Gate durchlaufen
> (siehe `.github/prompts/_partials/konventionen.md` und `.github/instructions/drift-policy.instructions.md`).

## Relevante Referenzen

- **Instruction:** `.github/instructions/drift-policy.instructions.md`
- **Push Gates:** `.github/instructions/drift-push-gates.instructions.md` (Gate 8 CI-Checks)
- **Bewertungssystem:** `.github/prompts/_partials/bewertungs-taxonomie.md`
- **Issue-Filing:** `.github/prompts/_partials/issue-filing.md`
- **CLI-Implementierung:** `src/drift/commands/` (Click-CLI-Subcommands)
- **Konfig:** `drift.example.yaml` (Referenz-Konfiguration)
- **Verwandte Prompts:** `drift-agent-ux.prompt.md` (Agent-UX-Perspektive), `drift-ci-gate.prompt.md` (CI-spezifische Validierung), `drift-signal-quality.prompt.md` (Signal-Korrektheit)

## Arbeitsmodus

- Systematisch, nicht explorativ: Jede Phase vollständig abschließen, bevor die nächste beginnt.
- Jeden CLI-Aufruf mit Exit-Code und relevanter Ausgabe dokumentieren.
- Unerwartetes Verhalten sofort als Beobachtung festhalten — nicht korrigieren.
- Unterscheide „Drift-Bug" von „Umgebungsproblem" (z.B. fehlende optionale Dependency, PATH-Problem).
- Sandbox-Destruction vermeiden: Sandbox nur dann löschen, wenn alle Tests abgeschlossen sind.

## Ziel

Verifiziere, dass alle Drift-CLI-Pfade — Installation, Analyse, Export, Konfiguration — korrekt funktionieren, sinnvolle Ergebnisse liefern und sich in CI-Pipelines zuverlässig verhalten.

## Erfolgskriterien

Die Aufgabe ist erst abgeschlossen, wenn du beantworten kannst:
- Sind alle CLI-Kommandos erreichbar und mit sinnvollen Defaults nutzbar?
- Produziert jedes Analyse-Kommando strukturierte, verwertbare Ergebnisse?
- Verhält sich Drift mit und ohne Konfigurationsdatei konsistent?
- Sind Exit-Codes, Fehlerverhalten und Edge-Cases CI-kompatibel?
- Welche CLI-Pfade haben echte Defekte vs. nur UX-Schwächen?

## Arbeitsregeln

- Jede Phase erzeugt eine Teiltabelle im Report (pass/review/fail mit Evidenz).
- Ein `fail` erfordert Beweis: Exit-Code, Error-Output oder fehlerhaftes Ergebnis zitieren.
- Ein `review` erfordert Begründung: Was stimmt, was ist unklar.
- Exit-Code 0 allein ist kein `pass` — der Output muss semantisch korrekt sein.
- CLI-Fehler sind erst dann Produkt-Bugs, wenn die Ausführungsumgebung verifiziert ist (richtige Python-Version, Drift installiert, Repo vorhanden).

## Bewertungs-Labels

Verwende ausschließlich Labels aus `.github/prompts/_partials/bewertungs-taxonomie.md`:

- **Ergebnis-Bewertung:** `pass` / `review` / `fail`
- **Test-Abdeckung:** `tested` / `skipped` / `blocked`
- **Risiko-Level:** `low` / `medium` / `high` / `critical`

## Artefakte

Erstelle Artefakte unter `work_artifacts/workflow_test_<YYYY-MM-DD>/`:

1. `discovery.md`
2. `analysis_results.md`
3. `export_results.md`
4. `config_results.md`
5. `edge_case_results.md`
6. `ci_realism_results.md`
7. `copilot_context_results.md`
8. `workflow_test_report.md`

## Workflow

### Phase 0: Sandbox erstellen

```bash
$sandbox = "work_artifacts/workflow_test_$(Get-Date -Format 'yyyy-MM-dd')"
New-Item -ItemType Directory -Path $sandbox -Force
```

### Phase 1: Installation & Discovery

```bash
drift --version
drift --help
```

Für jedes Top-Level-Kommando `drift <cmd> --help` ausführen.

**Test-Matrix:**

| Test | Kommando | Erwartung | Exit-Code | Ergebnis | Bewertung |
|------|----------|-----------|-----------|----------|-----------|
| Version abrufbar | `drift --version` | Versionsnummer | 0 | | |
| Help verfügbar | `drift --help` | Kommandoliste | 0 | | |
| Subcommands entdeckbar | `drift <cmd> --help` pro Kommando | Optionsliste | 0 | | |

### Phase 2: Kern-Analyse

```bash
drift scan
drift scan --max-findings 10
drift scan --response-detail detailed
drift analyze --repo .
drift analyze --repo . --format json
drift analyze --repo . --format sarif
```

**Test-Matrix:**

| Test | Kommando | Erwartung | Exit-Code | Ergebnis | Bewertung |
|------|----------|-----------|-----------|----------|-----------|
| Scan Baseline | `drift scan` | Findings-Ausgabe | 0 | | |
| Scan mit Limit | `drift scan --max-findings 10` | ≤ 10 Findings | 0 | | |
| Scan detailliert | `drift scan --response-detail detailed` | Erweiterte Details | 0 | | |
| Analyze Rich | `drift analyze --repo .` | Terminal-Report | 0 | | |
| Analyze JSON | `drift analyze --repo . --format json` | Valid JSON | 0 | | |
| Analyze SARIF | `drift analyze --repo . --format sarif` | Valid SARIF | 0 | | |

**JSON-Validierung:**
```bash
drift analyze --repo . --format json | python -c "import sys,json; json.load(sys.stdin); print('valid')"
```

**SARIF-Validierung (Pflichtfelder gemäß SARIF v2.1.0):**
- `$schema`, `version`, `runs[]`, `runs[].tool.driver.name`, `runs[].results[]`
- Jedes Result: `ruleId`, `message.text`, `locations[].physicalLocation.artifactLocation.uri`

### Phase 3: Export & Context-Outputs

```bash
drift export-context --repo . --format instructions
drift export-context --repo . --format prompt
drift export-context --repo . --format raw
drift copilot-context --repo .
```

**Test-Matrix:**

| Test | Kommando | Erwartung | Exit-Code | Ergebnis | Bewertung |
|------|----------|-----------|-----------|----------|-----------|
| Export instructions | `--format instructions` | Markdown-Output | 0 | | |
| Export prompt | `--format prompt` | Kompakte Regeln | 0 | | |
| Export raw | `--format raw` | Valid JSON | 0 | | |
| Copilot context | `copilot-context` | Markdown-Output | 0 | | |

**Raw-JSON-Validierung:**
```bash
drift export-context --repo . --format raw | python -c "import sys,json; d=json.load(sys.stdin); assert d.get('schema')=='drift-negative-context-v1', f'unexpected schema: {d.get(\"schema\")}'; print('valid')"
```

### Phase 3b: Stabilitäts-Check

Jeden Export-Befehl zweimal ausführen und diffen:
```bash
drift export-context --repo . --format instructions -o run1.md
drift export-context --repo . --format instructions -o run2.md
diff run1.md run2.md
```

Klassifikation: `stable` / `ordering-unstable` / `content-unstable`

### Phase 4: Konfiguration

Validiere das YAML-Config-Format:

```bash
# Standard: keine Konfiguration
drift analyze --repo . --format json > no_config.json

# Minimale Config anwenden
# (Verwende drift.example.yaml als Referenz)
drift analyze --repo . --format json --config drift.example.yaml > with_config.json
```

**Test-Matrix:**

| Test | Kommando | Erwartung | Exit-Code | Ergebnis | Bewertung |
|------|----------|-----------|-----------|----------|-----------|
| Ohne Config | `analyze --format json` | Default-Verhalten | 0 | | |
| Mit Example-Config | `analyze --config drift.example.yaml` | Config-respektiert | 0 | | |
| Ungültige Config | `analyze --config nonexistent.yaml` | Klarer Fehler | ≠0 | | |
| Leere Config | `echo '{}' > empty.yaml; analyze --config empty.yaml` | Default-Fallback | 0 | | |

### Phase 5: Edge-Cases & Fehlerbehandlung

```bash
drift analyze --repo /nonexistent
drift analyze --repo . --format unknown
drift scan --max-findings 0
drift scan --max-findings -1
drift export-context --repo . --format nonexistent
drift analyze --repo .  2>&1 | Out-Null; echo $LASTEXITCODE
```

**Test-Matrix:**

| Test | Kommando | Erwartung | Exit-Code | Fehlermeldung | Bewertung |
|------|----------|-----------|-----------|---------------|-----------|
| Nichtexist. Repo | `--repo /nonexistent` | Klarer Fehler | ≠0 | | |
| Ungültiges Format | `--format unknown` | Klarer Fehler | ≠0 | | |
| Limit 0 | `--max-findings 0` | Leer oder Fehler | | | |
| Negatives Limit | `--max-findings -1` | Fehler | ≠0 | | |
| Ungültiger Export | `export --format nonexistent` | Fehler | ≠0 | | |

**Fehler-Qualitätskriterien (pro Fehlerfall):**
1. Fehlermeldung enthält den fehlerhaften Parameterwert?
2. Fehlermeldung schlägt Korrektur vor?
3. Exit-Code unterscheidet Konfigurationsfehler von Analysefehlern?

### Phase 6: CI-Realism

Simuliere CI-typische Nutzung:

```bash
# Non-Interactive (kein TTY)
drift analyze --repo . --format json 2>&1 | Out-Null; echo $LASTEXITCODE

# Exit-Code-gesteuerte Entscheidung
drift analyze --repo . --exit-zero --format json > results.json; echo "Exit: $LASTEXITCODE"

# Stdout-Redirect (kein Terminal)
drift analyze --repo . --format json > /dev/null 2>&1; echo $LASTEXITCODE
```

**Realism-Checkliste:**

| Prüfpunkt | Ergebnis | Anmerkung |
|-----------|----------|-----------|
| `--exit-zero` produziert Exit 0 trotz Findings | | |
| JSON-Output nach stdout redirect noch valid | | |
| Kein interaktiver Prompt in Non-TTY | | |
| Fehler-Output nach stderr (nicht stdout) | | |
| Output-Encoding konsistent (UTF-8) | | |

### Phase 6b: CI-Kommando-Auswahl

Falls mehrere Analyse-Kommandos in CI nutzbar sind, Auswahlmatrix erstellen:

| Kriterium | `scan` | `analyze` | `export-context` |
|-----------|--------|-----------|-------------------|
| Laufzeit typisch | | | |
| Exit-Code nutzbar? | | | |
| Maschinenlesbar? | | | |
| Fail-on-finding? | | | |

### Phase 7: MCP & Explain (optional)

Falls verfügbar, auch diese Pfade testen:

```bash
drift explain <signal>
drift mcp --help
```

### Phase 7b: Copilot-Context-Integration

```bash
drift copilot-context --repo .
```

Bewerte:
- Ist der Output ein gültiges `.github/copilot-instructions.md`-Fragment?
- Enthält er aktionierbare Anweisungen (nicht nur Beschreibungen)?
- Referenziert er Drift-spezifische Signale konsistent?

### Phase 7c: Export-Context Konsistenz

Vergleiche alle drei Export-Formate auf inhaltliche Konsistenz:
- Gleiche Signale in allen Formaten referenziert?
- Gleiche Prioritätsreihenfolge?
- `raw`-Schema enthält alle Information aus `instructions` und `prompt`?

### Phase 8: Report erstellen

```markdown
# Drift Workflow Test Report

**Datum:** <YYYY-MM-DD>
**drift-Version:** [VERSION]
**Repository:** [REPO-NAME]
**Plattform:** [OS/SHELL]

## Summary

| Phase | Tests | Pass | Review | Fail | Blocked |
|-------|-------|------|--------|------|---------|
| Discovery | | | | | |
| Analyse | | | | | |
| Export | | | | | |
| Config | | | | | |
| Edge-Cases | | | | | |
| CI-Realism | | | | | |
| Optional | | | | | |
| **Gesamt** | | | | | |

## Defekte (fail)

| Phase | Test | Evidenz | Schwere | Empfohlene Aktion |
|-------|------|---------|---------|-------------------|

## Review-Items (review)

| Phase | Test | Beobachtung | Mögliche Ursache | Empfohlene Aktion |
|-------|------|-------------|-------------------|-------------------|

## CI-Empfehlung

| Use Case | Empfohlenes Kommando | Exit-Handling | Begründung |
|----------|---------------------|---------------|------------|

## Prioritäre Verbesserungen

1. [...]
2. [...]
3. [...]
```

## Entscheidungsregel

**Unterscheide konsequent:**
- `fail` = Drift produziert falsches Ergebnis oder bricht unerwartet ab → Produkt-Bug
- `review` = Ergebnis unklar oder möglicherweise korrekt aber nicht ideal → Klärungsbedarf
- `blocked` = Test konnte nicht ausgeführt werden wegen Umgebungsproblem → kein Drift-Bug

Ein CLI-Fehler ist erst dann ein Produkt-Bug, wenn die Ausführungsumgebung verifiziert ist (drift installiert, Repo existiert, Python-Version korrekt).

## GitHub-Issue-Erstellung

Am Ende des Workflows GitHub-Issues erstellen gemäß `.github/prompts/_partials/issue-filing.md`.

**Prompt-Kürzel für Titel:** `workflow-test`

### Issues erstellen für

- Alle `fail`-Bewertungen mit reproduzierbarer Evidenz
- `review`-Items, die auf einen Produkt-Bug hindeuten (nicht reine UX-Fragen)
- CI-Realism-Probleme, die Pipeline-Integration blockieren
- Interne Widersprüche zwischen `scan` und `analyze` für gleiche Eingabe

### Keine Issues erstellen für

- `blocked`-Items (Umgebungsprobleme, fehlende Dependencies)
- Subjektive Formatpräferenzen ohne funktionalen Impact
- Duplikate bereits existierender Issues

### Minimale und echte Test-Änderungen

**Wichtig:** Wenn ein Test ein neues Feature erfordert oder ein existierender Test angepasst werden muss:
- Minimale Fixtures sind erlaubt (z.B. leere Config-Dateien für Config-Tests).
- Code-Änderungen am Produkt selbst (src/drift/) sind **nicht** Teil dieses Prompts.
- Wenn ein Defekt eine Code-Änderung erfordert, erstelle ein Issue statt den Fix selbst vorzunehmen.
