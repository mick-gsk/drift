---
name: "Drift Signal Quality"
agent: agent
description: "Testet, ob Drift-Findings korrekt sind: Signal-Precision und -Recall messen, scan vs. analyze vergleichen, TP/FP/FN-Evidenz dokumentieren."
---

# Drift Signal Quality

Du validierst, ob Drift-Signale semantisch korrekt, vertrauenswürdig und stabil genug für nachgelagerte Workflows sind. Signalqualität hat Vorrang vor Kommando-Breite.

> **Pflicht:** Vor Ausführung dieses Prompts das Drift Policy Gate durchlaufen
> (siehe `.github/prompts/_partials/konventionen.md` und `.github/instructions/drift-policy.instructions.md`).

## Relevante Referenzen

- **Instruction:** `.github/instructions/drift-policy.instructions.md` (Policy §18: Audit-Pflicht bei Signalarbeit)
- **Bewertungssystem:** `.github/prompts/_partials/bewertungs-taxonomie.md`
- **Issue-Filing:** `.github/prompts/_partials/issue-filing.md`
- **Signal-Implementierung:** `src/drift/signals/` (15 Detektoren: PFS, AVS, MDS, EDS, TVS, SMS, DIA, BEM, TPD, GCD, NBV, BAT, ECM, COD, CCC)
- **Existierende Benchmarks:** `benchmark_results/ground_truth_labels.json` (Oracle-Quelle)
- **Verwandte Prompts:** `drift-agent-workflow-test.prompt.md` (Phase 1+2 testen Signale in Workflows)

## Arbeitsmodus

- Trenne Oracle-Fakten, CLI-Beobachtungen und Schlussfolgerungen in klar unterschiedliche Aussagen.
- Vergleiche konkurrierende Erklärungen, bevor du ein Signal als falsch oder korrekt bezeichnest.
- Verdichte große Ergebnismengen in entscheidungsorientierte Zusammenfassungen statt Raw-Output zu wiederholen.
- Mache Unsicherheit explizit, wenn der Oracle schwach oder unvollständig ist.
- Bevorzuge wenige starke, gut belegte Urteile gegenüber breiter aber flacher Abdeckung.

## Ziel

Bestimme, ob Drift die richtigen Architekturprobleme meldet, False Positives vermeidet und intern konsistent über Analysemodi bleibt.

## Erfolgskriterien

Die Aufgabe ist erst abgeschlossen, wenn du mit Evidenz beantworten kannst:
- Welche Signale produzierten True Positives, False Positives und False Negatives?
- Erzählen `scan` und `analyze` eine materiell konsistente Geschichte?
- Ist ein Signal zu verrauscht oder zu schwach für agent-gesteuerte Reparatur-Workflows?
- Welche Signal-Qualitäts-Verbesserungen sollten als nächstes priorisiert werden?

## Arbeitsregeln

- Evidenz-first. Für jede Qualitätsaussage die auslösende Datei, das Code-Pattern und die Drift-Ausgabe zitieren.
- Repo-realistische Fälle bevorzugen. Synthetische Fixtures nur verwenden, wenn das Repo keinen sauberen Oracle für ein gegebenes Signal bietet.
- Beobachtetes Verhalten von Urteil trennen.
- Wenn Signalqualität unklar ist: sagen welcher zusätzliche Oracle oder Benchmark nötig wäre.
- Signal-Vertrauenswürdigkeit ist wichtiger als Output-Volumen.

## Bewertungs-Labels

Verwende ausschließlich Labels aus `.github/prompts/_partials/bewertungs-taxonomie.md`:

- **Signal-Vertrauensstufe**: `trusted` / `needs_review` / `unsafe`
- **Actionability-Score**: `1 automated` / `2 guided` / `3 human-review` / `4 blocked`
- **Cross-Validation**: `metadata-only` / `priority-shift` / `contradiction`
- **Idempotenz**: `stable` / `ordering-unstable` / `content-unstable`

**Precision-Schwellen:**
- ≥ 70%: `trusted`
- 50–69%: `needs_review`
- < 50%: `unsafe`

**Actionability-Schwelle für Produktionseinsatz:** Score ≤ 2 = agent-tauglich, Score 3 = nur mit Maintainer-Freigabe.

## Artefakte

Erstelle Artefakte unter `work_artifacts/signal_quality_<YYYY-MM-DD>/`:

1. `signal_inventory.md`
2. `scan_results.json`
3. `analyze_results.json`
4. `oracle_cases.md`
5. `signal_quality_report.md`

## Workflow

### Phase 0: Signal-Inventar erstellen

Signale aus realer CLI-Ausgabe inventarisieren und Abkürzungen, Namen und verfügbare Beschreibungen erfassen.

Mindestens prüfen:
- Welche Signale sind direkt für User exponiert?
- Welche Kommandos können als Evidenzquellen für Signalverhalten dienen?
- Ist Signal-Level-Filterung verfügbar?

### Phase 1: Oracle-Set aufbauen

Für jedes getestete Signal einen kleinen, aber expliziten Oracle erstellen oder identifizieren.

**Oracle-Quellen (in Prioritätsreihenfolge):**
1. `benchmark_results/ground_truth_labels.json` — existierende Ground-Truth-Labels
2. Ein existierender Repo-Standort mit klar erklärbarem Architekturproblem
3. Ein fokussierter Sandbox-Fixture mit einem bekannten Violations-Pattern
4. Ein zuvor dokumentiertes Benchmark- oder Validierungsartefakt

**Mindestanforderung pro Signal:**
- ≥ 2 bestätigte True Positives (aus unterschiedlichen Dateien/Patterns)
- ≥ 1 bestätigter False-Positive-Gegenbeispielfall (Code, das ähnlich aussieht, aber kein Treffer sein sollte)

Für jeden Oracle-Fall dokumentieren:
- Erwartetes Signal
- Erwartetes Severity- oder Ranking-Verhalten (falls relevant)
- Warum dies als positiver Fall gelten sollte
- Was ein False Positive in der Nähe aussehen würde

### Synthetisches Fixture-Template

Wenn kein sauberer repo-interner Oracle-Fall existiert, erstelle unter `work_artifacts/signal_quality_<YYYY-MM-DD>/fixtures/` eine Datei pro Signal:

```python
# fixture_<SIGNAL>.py
# Signal: <SIGNAL_ABBREVIATION>
# Expected: 1 TP, 0 FP
# Description: <Warum dieses Muster das Signal triggern soll>

<minimal code pattern>
```

Pro Fixture dokumentiere explizit:
- Welche Code-Zeile genau das Signal triggern soll
- Was eine benachbarte nicht-verletzende Variante wäre (Precision/FP-Prüfung)
- Aus welcher `drift explain`-Ausgabe das Trigger-Muster abgeleitet wurde

### Phase 2: Repository-Ergebnisse messen

Beide Analyse-Modi ausführen:

```bash
drift scan --max-findings 25 --response-detail detailed
drift analyze --repo . --output-format json
```

Falls Signal-Filterung verfügbar, fokussierte Läufe für ausgewählte Signale testen.

Pro getestetem Signal erfassen:
- True Positives
- False Positives
- False Negatives
- Ambigue Fälle, die Maintainer-Urteil erfordern

### Severity-Kalibrierung

Für jeden TP zusätzlich bewerten:
- Ist die gemeldete Severity (`high`/`medium`/`low`) plausibel für den konkreten Code-Kontext?
- Wenn Severity falsch erscheint: Diskrepanz als `severity_mismatch` dokumentieren

### Stabilitäts-Check

`drift scan` und `drift analyze` je zweimal ausführen, ohne Code-Änderungen dazwischen:

```bash
drift scan --max-findings 25 --json > scan_run1.json
drift scan --max-findings 25 --json > scan_run2.json
drift analyze --repo . --output-format json > analyze_run1.json
drift analyze --repo . --output-format json > analyze_run2.json
```

Vergleich nach Entfernen nicht-deterministischer Metadaten.

Klassifikation gemäß Taxonomie: `stable` / `ordering-unstable` / `content-unstable`

### Phase 3: Cross-Validation

`scan` und `analyze` für denselben Repository-State vergleichen.

Prüfen, ob:
- Dieselben Hauptprobleme in beiden Ansichten erscheinen
- Die dominanten Signale konsistent genug gerankt sind, um Handlung zu leiten
- Der maschinenlesbare Output dieselbe Bedeutung wie die menschenlesbare Zusammenfassung bewahrt

### Cross-Validation-Tiefencheck

Pro Finding, das in beiden Kommandos auftaucht, vergleiche:
- Signal-ID oder -Bezeichnung: identisch?
- Severity: identisch?
- Betroffene Datei und Zeile: identisch?
- Beschreibungstext: semantisch konsistent?

Klassifikation pro Diskrepanz gemäß Taxonomie: `metadata-only` / `priority-shift` / `contradiction`

### Phase 4: Actionability bewerten

Für jedes getestete Signal beantworten:
- Kann ein Agent diesem Signal genug vertrauen, um einen Fix-Plan zu starten?
- Identifiziert der Output eine klare Ursache oder nur ein vages Symptom?
- Wäre eine autonome Änderung basierend auf diesem Signal sicher, riskant oder blockiert?

Actionability-Score gemäß Taxonomie vergeben: `1 automated` / `2 guided` / `3 human-review` / `4 blocked`

### Signal-to-Noise-Schwelle

Nach der TP/FP/FN-Messung:
- Geschätzte Precision pro Signal berechnen: `TP / (TP + FP)`
- Schwellenwerte für Urteil anwenden (siehe Bewertungs-Labels oben)
- Zusätzlich auf Repo-Ebene den Anteil voraussichtlich legitimer Findings berechnen

### Phase 5: Report erstellen

```markdown
# Drift Signal Quality Report

**Datum:** <YYYY-MM-DD>
**drift-Version:** [VERSION]
**Repository:** [REPO-NAME]

## Summary-Tabelle

| Signal | Oracle-Abdeckung | TP | FP | FN | Severity-Match | Severity-Mismatch | Precision | Actionability (1-4) | Vertrauensstufe | Anmerkungen |
|--------|------------------|----|----|----|----------------|-------------------|-----------|---------------------|-----------------|-------------|

## Cross-Validation

| Vergleich | Konsistent? | Klassifikation | Evidenz | Impact |
|-----------|-------------|----------------|---------|--------|

## Vertraute Signale (trusted)

[Liste]

## Review-pflichtige Signale (needs_review)

[Liste]

## Unsichere Signale (unsafe)

[Liste]

## Prioritäre Verbesserungen

1. [...]
2. [...]
3. [...]
```

## Entscheidungsregel

Wenn der Signal-Output nicht vertrauenswürdig genug für einen autonomen nächsten Schritt ist: das klar sagen. Unsicherheit nicht hinter einer generischen Zusammenfassung verstecken.

## GitHub-Issue-Erstellung

Am Ende des Workflows GitHub-Issues erstellen gemäß `.github/prompts/_partials/issue-filing.md`.

**Prompt-Kürzel für Titel:** `signal-quality`

### Issues erstellen für

- Signale mit Bewertung `unsafe`
- Wiederholte oder schwerwiegende `needs_review`-Fälle
- Cross-Validation-Mismatches zwischen `scan` und `analyze`
- Fehlende Erklärungen, Filterung oder Output-Struktur, die zuverlässige Signalevaluation verhindert

### Keine Issues erstellen für

- Einmaliges lokales Umgebungsrauschen
- Fälle, in denen der Oracle selbst schwach ist und das Produktproblem nicht reproduzierbar
- Duplikate bereits existierender Issues
