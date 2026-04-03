---
name: "Drift Field Test"
agent: agent
description: "Smoke-Test: Funktioniert drift in diesem Repo? Installation, Discovery, Erst-Analyse, Output-Qualitaet, Konfiguration."
---

# Drift Field Test

Du testest ob der Drift-Analyzer in einem beliebigen Repository funktioniert — vom ersten Kommando bis zum verwertbaren Ergebnis. Kein Drift-internes Wissen vorausgesetzt.

> **Pflicht:** Vor Ausführung dieses Prompts das Drift Policy Gate durchlaufen
> (siehe `.github/prompts/_partials/konventionen.md` und `.github/instructions/drift-policy.instructions.md`).

## Relevante Referenzen

- **Bewertungssystem:** `.github/prompts/_partials/bewertungs-taxonomie.md`
- **Issue-Filing:** `.github/prompts/_partials/issue-filing-external.md`
- **Konventionen:** `.github/prompts/_partials/konventionen.md`
- **Verwandte Prompts:** `drift-finding-audit.prompt.md` (Tiefenprüfung), `drift-context-eval.prompt.md` (Kontext-Qualität)

## Scope

- **Testet:** Die Drift-CLI und ihre Outputs
- **Testet NICHT:** Ob das Ziel-Repo Architekturprobleme hat
- **Issues gehen an:** `sauremilk/drift` — nicht ans Ziel-Repo

## Arbeitsmodus

- Interagiere als Agent ohne Drift-Vorwissen — nur CLI-Signale nutzen.
- Dokumentiere jeden Schritt mit Kommando, Exit-Code und relevantem Output.
- Unterscheide Drift-Bugs von Umgebungsproblemen (falsche Python-Version, fehlendes Git, etc.).
- Bewerte Output-Qualität aus Agent-Perspektive: Kann ein Agent damit weiterarbeiten?

## Ziel

Bestimme, ob drift in diesem Repository installierbar, ausführbar und nützlich ist — mit minimalem Setup und ohne Konfiguration.

## Erfolgskriterien

Die Aufgabe ist erst abgeschlossen, wenn du beantworten kannst:
- Ist drift installiert und aufrufbar?
- Produziert `drift analyze` verwertbare Ergebnisse für dieses Repo?
- Sind die Outputs strukturell korrekt (valid JSON, plausible Severity-Verteilung)?
- Funktioniert `drift init` und erzeugt es eine sinnvolle Konfiguration?
- Welche Probleme sind Drift-Bugs vs. Umgebungsprobleme?

## Bewertungs-Labels

Verwende ausschließlich Labels aus `.github/prompts/_partials/bewertungs-taxonomie.md`:

- **Ergebnis-Bewertung:** `pass` / `review` / `fail`
- **Test-Abdeckung:** `tested` / `skipped` / `blocked`
- **Risiko-Level:** `low` / `medium` / `high` / `critical`

## Artefakte

Erstelle Artefakte unter `work_artifacts/field_test_<YYYY-MM-DD>/`:

1. `prerequisites.md`
2. `discovery.md`
3. `analysis_results.json`
4. `output_quality.md`
5. `config_results.md`
6. `field_test_report.md`

## Workflow

### Phase 0: Voraussetzungen prüfen

```bash
python --version          # ≥ 3.11 erforderlich
git --version             # Git muss vorhanden sein
drift --version           # drift muss installiert sein
git log --oneline -5      # Git-History vorhanden?
```

**Repo-Profil erfassen:**

| Eigenschaft | Wert |
|-------------|------|
| Repository | [OWNER/NAME] |
| Sprache(n) | [Python / TypeScript / Mixed / Andere] |
| Profil | [Library / Framework / Application / Monorepo] |
| Ungefähre Größe | [Dateianzahl oder LOC] |
| Git-Commits | [Anzahl oder "shallow clone"] |
| drift-Version | [VERSION] |

**Bewertung:**

| Voraussetzung | Status | Bewertung |
|---------------|--------|-----------|
| Python ≥ 3.11 | | `pass` / `fail` |
| Git verfügbar | | `pass` / `fail` |
| drift installiert | | `pass` / `fail` |
| Git-History vorhanden | | `pass` / `review` (shallow) / `fail` |

> **Bei `fail` in Python oder drift:** Abbruch — kein Drift-Bug, Umgebungsproblem.
> **Bei `review` in Git-History:** Weiter, aber Temporal-Signale (TVS, SMS, ECM) werden eingeschränkt sein — als `skipped` dokumentieren, nicht als `fail`.

### Phase 1: Discovery

```bash
drift --help
```

Für jedes sichtbare Top-Level-Kommando:
```bash
drift <command> --help
```

**Bewertung:**

| Test | Kommando | Exit-Code | Bewertung |
|------|----------|-----------|-----------|
| Help verfügbar | `drift --help` | | |
| Subcommands entdeckbar | `drift <cmd> --help` | | |

### Phase 2: Erst-Analyse

```bash
drift analyze --repo . --format json > analysis.json
drift analyze --repo .
drift scan --max-findings 15
```

**Bewertung:**

| Test | Kommando | Exit-Code | Findings | Bewertung |
|------|----------|-----------|----------|-----------|
| JSON-Analyse | `analyze --format json` | | [Anzahl] | |
| Rich-Analyse | `analyze` | | [Ausgabe vorhanden?] | |
| Scan | `scan --max-findings 15` | | [Anzahl] | |

**JSON-Validierung:**
```bash
python -c "import json,sys; d=json.load(open('analysis.json')); print(f'findings: {len(d.get(\"findings\", d.get(\"results\", [])))}'); print('valid JSON')"
```

### Phase 3: Output-Qualitätsprüfung

Für die JSON-Analyse-Ergebnisse prüfen:

**Strukturelle Korrektheit:**
- [ ] Valid JSON
- [ ] Findings-Array vorhanden
- [ ] Jedes Finding hat: Signal-ID, betroffene Datei, Severity, Beschreibung
- [ ] Mindestens ein Finding vorhanden (bei nicht-trivialem Repo)

**Plausibilität:**
- [ ] Severity-Verteilung nicht einseitig (nicht alles `high` oder alles `low`)
- [ ] Betroffene Dateien existieren tatsächlich im Repo
- [ ] Signal-Typen sind divers (nicht nur ein Signal)
- [ ] Beschreibungen sind für dieses Repo kontextuell plausibel

**Laufzeit:**

| Kommando | Dauer | Bewertung |
|----------|-------|-----------|
| `analyze --format json` | [s] | `acceptable` / `tolerable` / `disruptive` |
| `scan` | [s] | |

> Latenz-Klassifikation: < 30s = `acceptable`, 30-120s = `tolerable`, > 120s = `disruptive`
> (Schwellen höher als bei internen Prompts, da externe Repos beliebig groß sein können)

### Phase 4: Konfiguration testen

```bash
drift init --repo .
drift validate --repo .
drift config show --repo .
```

**Bewertung:**

| Test | Kommando | Exit-Code | Bewertung |
|------|----------|-----------|-----------|
| Init erzeugt Config | `drift init` | | |
| Config ist valid | `drift validate` | | |
| Config zeigt Werte | `drift config show` | | |

**Config-Qualität (nach `drift init`):**
- [ ] `drift.yaml` wurde erzeugt
- [ ] Include/Exclude-Patterns passen zum Repo (richtige Dateiendungen, sinnvolle Ausschlüsse)
- [ ] Kein offensichtlicher Fehl-Detect (z.B. TypeScript-Patterns in reinem Python-Repo)

**Analyse mit Config wiederholen:**
```bash
drift analyze --repo . --format json > analysis_with_config.json
```

Vergleich: Ändern sich die Ergebnisse qualitativ mit Config vs. ohne?

### Phase 5: Report erstellen

```markdown
# Drift Field Test Report

**Datum:** <YYYY-MM-DD>
**drift-Version:** [VERSION]
**Repository:** [OWNER/REPO-NAME]
**Repo-Profil:** [Library / Framework / Application / Monorepo]
**Sprache(n):** [Python / TypeScript / Mixed]

## Repo-Profil

[Tabelle aus Phase 0]

## Summary

| Phase | Tests | Pass | Review | Fail | Blocked |
|-------|-------|------|--------|------|---------|
| Voraussetzungen | | | | | |
| Discovery | | | | | |
| Erst-Analyse | | | | | |
| Output-Qualität | | | | | |
| Konfiguration | | | | | |
| **Gesamt** | | | | | |

## Defekte (fail)

| Phase | Test | Evidenz | Risiko | Generalisierbar? |
|-------|------|---------|--------|------------------|

## Review-Items

| Phase | Test | Beobachtung | Mögliche Ursache |
|-------|------|-------------|------------------|

## Gesamtbewertung

- drift funktioniert in diesem Repo: [JA / TEILWEISE / NEIN]
- Output-Qualität: [pass / review / fail]
- Empfohlener nächster Schritt: [finding-audit / context-eval / keiner — Blocker zuerst beheben]
```

## Entscheidungsregel

Wenn drift abstürzt oder keine Ergebnisse liefert: `fail`. Wenn Ergebnisse kommen aber fragwürdig sind: `review`. Nur wenn Ergebnisse strukturell korrekt UND kontextuell plausibel sind: `pass`.

## GitHub-Issue-Erstellung

Am Ende des Workflows GitHub-Issues auf `sauremilk/drift` erstellen gemäß `.github/prompts/_partials/issue-filing-external.md`.

**Prompt-Kürzel für Titel:** `field-test`

### Issues erstellen für

- Abstürze oder Fehler, die nicht durch Umgebungsprobleme erklärbar sind
- Strukturell kaputte Outputs (invalid JSON, fehlende Felder)
- `drift init` erzeugt offensichtlich falsche Konfiguration für den Repo-Typ
- Laufzeit > 120s bei normalgroßem Repo (< 5000 Dateien)

### Keine Issues erstellen für

- Fehlende Python ≥ 3.11 oder Git (Umgebungsproblem)
- Findings, die inhaltlich fragwürdig sind (→ das testet `drift-finding-audit`)
- Export-Qualität (→ das testet `drift-context-eval`)
