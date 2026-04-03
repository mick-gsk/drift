---
name: "Drift CI Gate"
agent: agent
description: "Validiert, ob Drift zuverlässig genug für CI-Pipelines und Pre-Push-Gates ist: Exit-Codes, Fail-On-Verhalten, Idempotenz, Output-Verträge und maschinenlesbare Artefakte."
---

# Drift CI Gate

Du validierst, ob Drift zuverlässig genug für den Einsatz in CI-Pipelines, Pre-Push-Checks und automatisierten Quality-Gates ist.

> **Pflicht:** Vor Ausführung dieses Prompts das Drift Policy Gate durchlaufen
> (siehe `.github/prompts/_partials/konventionen.md` und `.github/instructions/drift-policy.instructions.md`).

## Relevante Referenzen

- **Instruction:** `.github/instructions/drift-push-gates.instructions.md` (Pre-Push-Gate-Definitionen)
- **Instruction:** `.github/instructions/drift-policy.instructions.md`
- **Bewertungssystem:** `.github/prompts/_partials/bewertungs-taxonomie.md`
- **Issue-Filing:** `.github/prompts/_partials/issue-filing.md`
- **Verwandte Prompts:** `drift-agent-workflow-test.prompt.md` (Phase 5b + Phase 8 testen Exit-Codes/Edge-Cases)
- **SARIF-Spezifikation:** https://docs.oasis-open.org/sarif/sarif/v2.1.0/

## Arbeitsmodus

- Unterscheide beobachtetes Prozessverhalten von abgeleiteten Vertragsverletzungen.
- Vergleiche wiederholte Läufe sorgfältig, bevor du etwas als flaky oder deterministisch einstufst.
- Bevorzuge kompakte Matrizen statt Prosa beim Prüfen von Exit-Code- und Format-Konsistenz.
- Benenne für jeden Defekt die exakte operationelle Konsequenz für CI-Nutzer.
- Vermeide überzogenes Vertrauen, wenn ein Fehler umgebungsspezifisch sein könnte.

## Ziel

Bestimme, ob Drift als Production-Gate vertrauenswürdig ist, indem du Exit-Code-Verhalten, Wiederholbarkeit, Randbedingungen und maschinenlesbare Outputs testest.

## Erfolgskriterien

Die Aufgabe ist erst abgeschlossen, wenn du beantworten kannst:
- Stimmen Exit-Codes mit dem dokumentierten oder impliziten Vertrag überein?
- Sind wiederholte Läufe auf demselben Repo-State stabil genug für CI?
- Sind maschinenlesbare Formate valide und entscheidungsfertig?
- Welche Failure-Modi würden Drift in Pipelines unsicher oder störend machen?

## Arbeitsregeln

- Fokus auf operationelle Zuverlässigkeit, nicht auf Signal-Semantik.
- Gleiche Checks mehrfach ausführen, wenn Stabilität relevant ist.
- Nicht-Determinismus als Produktrisiko behandeln, sofern nicht klar gerechtfertigt.
- Maschinenlesbare Evidenz bevorzugen, wenn das Kommando es unterstützt.
- Produktdefekte von umgebungsspezifischen Failures unterscheiden.

## Bewertungs-Labels

Verwende ausschließlich Labels aus `.github/prompts/_partials/bewertungs-taxonomie.md`:

- **Ergebnis-Bewertung** pro Test: `pass` / `review` / `fail`
- **Abdeckungs-Status**: `tested` / `skipped` / `blocked`
- **Idempotenz-Klassifikation**: `stable` / `ordering-unstable` / `content-unstable`

## Artefakte

Erstelle Artefakte unter `work_artifacts/ci_gate_<YYYY-MM-DD>/`:

1. `gate_runs/`
2. `exit_code_matrix.md`
3. `idempotence_diff.md`
4. `sarif_validation.md`
5. `ci_gate_report.md`

## Workflow

### Phase 0: Gate-relevante Kommandos inventarisieren

Identifiziere die für CI relevanten Kommandos und Optionen, insbesondere:
- `check` (mit `--fail-on`, `--json`, `--compact`, `--output-format`)
- `validate`
- JSON- und SARIF-Output-Pfade
- Baseline-gesteuerte Gate-Flows

Verifiziere den Exit-Code-Vertrag anhand der CLI-Hilfe (`drift check --help`). Falls die Hilfe keine Exit-Codes dokumentiert, dokumentiere das als fehlenden Vertrag.

### Phase 1: Exit-Code-Verträge testen

#### Exit-Code-Baseline

| Code | Erwartete Bedeutung |
|------|---------------------|
| `0` | Kommando erfolgreich, Gate bestanden |
| `1` | Kommando erfolgreich, Gate durchgefallen (Findings über Schwelle) |
| `2` | Usage-, Config- oder Input-Fehler |
| `>2` | Interner oder unerwarteter Laufzeitfehler |

Falls die CLI-Hilfe einen abweichenden Vertrag definiert: diesen verwenden und Abweichung dokumentieren.

#### Phase 1a: Clean-Pass-Szenario

```bash
drift check --fail-on none --json --compact
```
Erwartung: Exit-Code 0, unabhängig von Finding-Anzahl.

#### Phase 1b: Fail-Threshold-Szenario

```bash
drift check --fail-on medium
drift check --fail-on high --output-format rich
```
Erwartung: Exit-Code 1, wenn Findings der entsprechenden Severity existieren. Output muss die auslösenden Findings identifizieren.

#### Phase 1c: Usage-Error-Szenario

```bash
drift check --fail-on invalid_level
```
Erwartung: Exit-Code 2, strukturierte Fehlermeldung (kein Stack-Trace).

#### Phase 1d: Baseline-gesteuertes Szenario

Gleiches Gate-Kommando mit und ohne Baseline-Datei ausführen. Prüfen, ob Baseline-Präsenz nur die Gate-Entscheidung ändert, nicht den Finding-Set.

### Phase 2: Idempotenz testen

Gleiches Gate-Kommando mindestens dreimal auf unverändertem Repo-State ausführen.

Pro Lauf diese Dimensionen unabhängig vergleichen:

| Dimension | Was prüfen |
|-----------|------------|
| Exit-Code-Stabilität | Alle Läufe gleicher Exit-Code |
| Finding-Stabilität | Gesamtzahl, pro-Severity-Zähler und Finding-IDs stabil |
| Output-Stabilität | JSON-Felder identifizieren, die sich zwischen Läufen ändern |

Klassifikation gemäß Taxonomie (`stable` / `ordering-unstable` / `content-unstable`).

Ein Gate mit `content-unstable`-Varianz ist **nicht CI-ready**.

**Hinweis zu `ordering-unstable`:** Wenn Findings in zufälliger Reihenfolge erscheinen, kann der JSON-Diff groß wirken, obwohl der Inhalt identisch ist. Normalisiere die Finding-Liste (sortiert nach Signal+Datei+Zeile) vor dem Vergleich, um `ordering-unstable` von `content-unstable` zu trennen.

### Phase 3: Randbedingungen testen

CI-relevante Boundary-Inputs:
- Sehr niedriges und sehr hohes `--max-findings`
- Baseline vorhanden vs. abwesend
- `--compact` vs. `--output-format rich`
- Read-only oder nicht-schreibbare Output-Zieldateien

Falls eine Randbedingung nicht testbar ist: Grund dokumentieren und nächstbesten Proxy angeben.

### Phase 4: Maschinenlesbare Outputs validieren

#### JSON-Mindestvertrag

Für JSON-Outputs mindestens prüfen:
- Top-Level-Objekt parst fehlerfrei
- Stabile Top-Level-Keys über Läufe hinweg vorhanden
- Findings als strukturierte Records, nicht als Prosa
- Folgende Felder maschinenextrahierbar (exakte Feldnamen aus `drift check --json` Output ableiten):
  - Finding-Severity (z.B. `severity`)
  - Signal-Bezeichnung (z.B. `signal`)
  - Dateipfad (z.B. `file_path` oder `file`)
- Diff-barkeit: Zweiter Lauf produziert JSON-Diff klassifizierbar als `stable`, `ordering-unstable` oder `content-unstable`

#### SARIF-Mindestvertrag

Für SARIF-Outputs mindestens prüfen (gemäß SARIF v2.1.0 Spec):
- Datei ist valides JSON
- `$schema`-Feld vorhanden
- `version` = `"2.1.0"`
- `runs` Key auf Top-Level mit `runs[0].tool.driver`
- `runs[0].results` existiert
- Jedes Result enthält:
  - `ruleId` (stabile Signal-ID)
  - `message.text` (Beschreibung)
  - `locations[0].physicalLocation.artifactLocation.uri` (Dateipfad)
  - `locations[0].physicalLocation.region.startLine` (Zeilennummer, falls verfügbar)
- Genug Location-Information für GitHub-Annotations-Kontext

Falls ein Mindestvertrag scheitert: exaktes fehlendes Feld und Schweregrad für Automation dokumentieren.

### Phase 4b: CI-Realism-Checks

Verhalten unter tatsächlichen CI-Pipeline-Bedingungen prüfen:

- **Nicht-schreibbarer Output-Pfad**: JSON/SARIF an nicht-schreibbaren Pfad umleiten. Erwartung: Graceful Fail mit actionabler Fehlermeldung und non-zero Exit-Code.
- **Nicht-interaktiver Output**: Mit `--compact` oder `--json` in Datei pipsen (kein TTY). Erwartung: Output enthält keine ANSI-Escape-Codes oder Progress-Spinner.
- **Großes Compact-Output**: Bei vielen Findings prüfen, ob `--compact` strukturierte Daten nicht abschneidet.
- **Exit-Code-Verträge**: Prüfen, ob Exit-Codes konsistent sind, wenn stdout/stderr umgeleitet werden.
- **Retry-Verhalten**: Identisches Kommando nach einem Fehler erneut ausführen — produziert es konsistente Ergebnisse?

#### Empfohlenes CI-Kommando

Am Ende von Phase 4b genau ein Default-CI-Gate-Kommando festlegen und in je einem Satz begründen:

| Kriterium | Begründung |
|-----------|------------|
| **Determinismus** | Warum produziert das Kommando stabile Ausgabe? |
| **Maschinenlesbarkeit** | Warum kann Downstream-Automation es zuverlässig parsen? |
| **Noise-Level** | Warum ist die `--fail-on`-Schwelle passend? |
| **Adoption** | Kann ein neues Team es ohne Extra-Konfiguration in einen Workflow einbauen? |

### Phase 5: Report erstellen

```markdown
# Drift CI Gate Report

**Datum:** <YYYY-MM-DD>
**drift-Version:** [VERSION]
**Repository:** [REPO-NAME]

## Gate-Urteil

`ready` / `conditional` / `unsafe`

## Exit-Code-Matrix

| Kommando | Erwartet | Beobachtet | Stabil? | Bewertung |
|----------|----------|------------|---------|-----------|

## Idempotenz

| Lauf-Set | Stabil? | Klassifikation | Evidenz | Anmerkungen |
|----------|---------|----------------|---------|-------------|

## Maschinenlesbare Outputs

| Format | Valide? | Automation-tauglich? | Fehlende Felder | Anmerkungen |
|--------|---------|---------------------|-----------------|-------------|

## Pipeline-Risiken

1. [...]
2. [...]

## Empfohlene CI-Policy

**Kommando:** `[exaktes Kommando]`

| Kriterium | Bewertung |
|-----------|-----------|
| Determinismus | [ein Satz] |
| Maschinenlesbarkeit | [ein Satz] |
| Noise-Level | [ein Satz] |
| Adoption | [ein Satz] |
```

## Entscheidungsregel

Wenn der Output-Vertrag nicht stabil genug für Automation ist, das Tool nicht als CI-ready bezeichnen.

## GitHub-Issue-Erstellung

Am Ende des Workflows GitHub-Issues erstellen gemäß `.github/prompts/_partials/issue-filing.md`.

**Prompt-Kürzel für Titel:** `ci-gate`

### Issues erstellen für (Prioritätsreihenfolge)

1. **CI-Blocker** — Exit-Code-Mismatches (beobachtet ≠ Vertrag)
2. **Flaky-Verhalten** — `content-unstable` Varianz bei identischem Repo-State
3. **Format-Defekte** — JSON oder SARIF verletzt Mindestvertrag
4. **Ambigue Gate-Semantik** — technisch konsistent, aber zu unklar für sichere CI-Adoption

### Keine Issues erstellen für

- Vorübergehende lokale Runner-Failures ohne Produktbezug
- Bereits bekannte Issues, die den Defekt vollständig abdecken
- Test-Szenarien außerhalb des Kommandovertrags
