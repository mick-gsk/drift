---
name: "Drift Finding Audit"
agent: agent
description: "Tiefenpruefung: Sind Drift-Findings fuer dieses Repo korrekt? TP/FP/FN messen, Signal-Precision berechnen, Severity kalibrieren."
---

# Drift Finding Audit

Du prüfst, ob die Drift-Findings für ein beliebiges Repository semantisch korrekt sind. Du baust einen Oracle aus der Repo-Architektur auf und misst Signal-Precision und -Recall.

> **Pflicht:** Vor Ausführung dieses Prompts das Drift Policy Gate durchlaufen
> (siehe `.github/prompts/_partials/konventionen.md` und `.github/instructions/drift-policy.instructions.md`).

> **Voraussetzung:** `drift-field-test.prompt.md` sollte vorher gelaufen sein und `pass` ergeben haben.

## Relevante Referenzen

- **Bewertungssystem:** `.github/prompts/_partials/bewertungs-taxonomie.md`
- **Issue-Filing:** `.github/prompts/_partials/issue-filing-external.md`
- **Konventionen:** `.github/prompts/_partials/konventionen.md`
- **Verwandte Prompts:** `drift-field-test.prompt.md` (Voraussetzung), `drift-context-eval.prompt.md` (Kontext-Qualität)

## Scope

- **Testet:** Ob Drift-Signale für DIESES Repo korrekt feuern
- **Testet NICHT:** Ob das Ziel-Repo repariert werden sollte
- **Issues gehen an:** `mick-gsk/drift` — nicht ans Ziel-Repo

## Arbeitsmodus

- Trenne Oracle-Fakten (was du über die Architektur weißt) von Drift-Beobachtungen (was drift meldet) von Urteilen (TP/FP/FN).
- Baue den Oracle VOR der Analyse auf — nicht im Nachhinein passend machen.
- Bevorzuge wenige starke, gut belegte Urteile gegenüber breiter aber flacher Abdeckung.
- Mache Unsicherheit explizit, wenn du die Architekturentscheidung des Repos nicht sicher beurteilen kannst.
- Wenn ein Signal in diesem Repo-Typ generell unpassend ist (z.B. AVS in einem Framework, das Imports zwischen Layern erwartet), dokumentiere das als systematisches FP-Pattern, nicht als Einzelfall.

## Ziel

Bestimme, ob Drift in diesem Repository die richtigen Probleme findet, False Positives vermeidet und Severities korrekt kalibriert — mit einem aus der Repo-Architektur abgeleiteten Oracle.

## Erfolgskriterien

Die Aufgabe ist erst abgeschlossen, wenn du beantworten kannst:
- Welche Signals produzieren in diesem Repo TP, FP und FN?
- Wie hoch ist die geschätzte Precision pro Signal?
- Passt die gemeldete Severity zum tatsächlichen Architektur-Kontext?
- Erzählen `scan` und `analyze` eine konsistente Geschichte?
- Welche FP-Patterns sind möglicherweise systematisch (betreffen ähnliche Repos)?

## Bewertungs-Labels

Verwende ausschließlich Labels aus `.github/prompts/_partials/bewertungs-taxonomie.md`:

- **Signal-Vertrauensstufe:** `trusted` / `needs_review` / `unsafe`
- **Actionability-Score:** `1 automated` / `2 guided` / `3 human-review` / `4 blocked`
- **Cross-Validation:** `metadata-only` / `priority-shift` / `contradiction`

**Precision-Schwellen:**
- ≥ 70%: `trusted`
- 50–69%: `needs_review`
- < 50%: `unsafe`

## Artefakte

Erstelle Artefakte unter `work_artifacts/finding_audit_<YYYY-MM-DD>/`:

1. `repo_profile.md`
2. `oracle.md`
3. `analyze_results.json`
4. `scan_results.json`
5. `tp_fp_fn_classification.md`
6. `finding_audit_report.md`

## Workflow

### Phase 0: Architektur-Profil erstellen

Analysiere das Repository, um einen informierten Oracle aufzubauen:

```bash
# Struktur verstehen
find . -type f -name "*.py" -o -name "*.ts" -o -name "*.tsx" | head -50
# oder: Get-ChildItem -Recurse -Include *.py,*.ts,*.tsx | Select-Object -First 50

# README lesen
cat README.md 2>/dev/null || cat readme.md 2>/dev/null

# Ordnerstruktur
ls -la  # oder: Get-ChildItem
```

**Repo-Profil:**

| Eigenschaft | Wert |
|-------------|------|
| Repository | [OWNER/NAME] |
| Architektur-Typ | [Monolith / Microservice / Library / Framework / Monorepo] |
| Sprache(n) | [Python / TypeScript / Mixed] |
| Framework(s) | [Django / Flask / FastAPI / Express / None / ...] |
| Ungefähre Größe | [Dateien / LOC] |
| Bekannte Architekturentscheidungen | [z.B. "Django-apps-Struktur", "Hexagonal", "Layered"] |

### Phase 1: Oracle aufbauen

**VOR der Drift-Analyse** — nicht im Nachhinein anpassen.

Oracle besteht aus zwei Teilen:

**A) Erwartete Findings (5-10 Stellen):**

Identifiziere Stellen, an denen du architektonische Probleme erwartest. Für jede:

| # | Datei/Bereich | Erwartetes Signal | Erwartete Severity | Begründung |
|---|---------------|-------------------|--------------------|------------|
| 1 | | | | |
| ... | | | | |

Typische Quellen für erwartete Findings:
- Offensichtliche Schichtverletzungen (z.B. DB-Import in View-Layer)
- Code-Duplikation über Module hinweg
- Inkonsistente Fehlerbehandlung
- Fehlende oder veraltete Dokumentation
- Komplexe Funktionen ohne klare Zerlegung

**B) Erwartete Nicht-Findings (3-5 Stellen):**

Identifiziere Stellen, an denen kein Finding kommen sollte:

| # | Datei/Bereich | Warum kein Finding | Welches Signal könnte fälschlich feuern |
|---|---------------|--------------------|-----------------------------------------|
| 1 | | | |
| ... | | | |

Typische Nicht-Finding-Stellen:
- Framework-idiomatische Imports (z.B. Django `from models import *` in admin.py)
- Bewusste Architekturentscheidungen (z.B. Monolith statt Microservice)
- Testcode mit absichtlich abweichenden Patterns
- Vendored/third-party Code

> **Oracle-Qualität:** Der Oracle ist nur so stark wie dein Verständnis der Repo-Architektur. Wenn du eine Stelle nicht sicher beurteilen kannst, markiere sie als `uncertain` und schließe sie aus der Precision-Berechnung aus.

### Phase 2: Analyse ausführen

```bash
drift analyze --repo . --format json > analyze_results.json
drift scan --max-findings 25 --response-detail detailed > scan_results.json
```

Optional bei vorhandener Git-History:
```bash
drift diff --repo .
```

### Phase 3: Oracle-Abgleich

Jeden Oracle-Fall gegen die Drift-Ergebnisse prüfen:

**A) Erwartete Findings:**

| # | Oracle-Erwartung | Drift-Ergebnis | Klassifikation | Anmerkung |
|---|------------------|----------------|----------------|-----------|
| 1 | [Signal X in Datei Y] | [Gefunden / Nicht gefunden / Anderes Signal] | `TP` / `FN` | |
| ... | | | | |

**B) Erwartete Nicht-Findings:**

| # | Oracle-Erwartung (kein Finding) | Drift-Ergebnis | Klassifikation | Anmerkung |
|---|--------------------------------|----------------|----------------|-----------|
| 1 | [Kein AVS in Z] | [Korrekt kein Finding / Fälschlich gemeldet] | `TN` / `FP` | |
| ... | | | | |

**C) Unerwartete Findings (von Drift gemeldet, nicht im Oracle):**

Für jedes Finding, das nicht im Oracle war:

| Signal | Datei | Severity | Plausibel? | Klassifikation | Anmerkung |
|--------|-------|----------|------------|----------------|-----------|
| | | | [Ja/Nein/Unklar] | `TP` / `FP` / `uncertain` | |

### Phase 4: Signal-Precision berechnen

Pro Signal mit mindestens 2 Datenpunkten:

| Signal | TP | FP | FN | Uncertain | Precision | Vertrauensstufe |
|--------|----|----|----|-----------|-----------|-----------------|
| | | | | | `TP/(TP+FP)` | `trusted`/`needs_review`/`unsafe` |

> **Minimum für Aussage:** Mindestens 2 TP + 1 FP-Gegenbeispiel pro Signal für eine belastbare Precision-Schätzung. Bei weniger Datenpunkten als `insufficient data` markieren.

### Phase 5: Severity-Kalibrierung

Für jeden TP:

| Finding | Gemeldete Severity | Erwartete Severity | Match? | Anmerkung |
|---------|--------------------|--------------------|--------|-----------|
| | | | [Ja / Zu hoch / Zu niedrig] | |

Systematische Muster identifizieren:
- Tendiert Drift bei diesem Repo-Typ zu überhöhter Severity?
- Gibt es Signale, deren Severity konsistent falsch kalibriert ist?

### Phase 6: Cross-Validation

`scan` und `analyze` für denselben Repo-State vergleichen:

| Attribut | analyze | scan | Konsistenz |
|----------|---------|------|------------|
| Top-Findings stimmen überein? | | | `metadata-only` / `priority-shift` / `contradiction` |
| Signal-Verteilung ähnlich? | | | |
| Severity-Ranking konsistent? | | | |

### Phase 7: Report erstellen

```markdown
# Drift Finding Audit Report

**Datum:** <YYYY-MM-DD>
**drift-Version:** [VERSION]
**Repository:** [OWNER/REPO-NAME]
**Repo-Typ:** [Architektur-Typ + Framework]

## Repo-Profil

[Tabelle aus Phase 0]

## Oracle-Zusammenfassung

- Erwartete Findings: [N]
- Erwartete Nicht-Findings: [N]
- Oracle-Qualität: [stark / mittel / schwach — basierend auf Architektur-Vorwissen]

## Signal-Precision

| Signal | TP | FP | FN | Precision | Vertrauensstufe | Actionability |
|--------|----|----|----|-----------|-----------------|---------------|

## Severity-Kalibrierung

| Tendenz | Betroffene Signale | Impact |
|---------|--------------------|----- --|

## Cross-Validation

| Vergleich | Klassifikation | Evidenz |
|-----------|----------------|---------|

## Systematische FP-Patterns

[Patterns, die wahrscheinlich auch in ähnlichen Repos auftreten]

| Pattern | Betroffenes Signal | Repo-Typ | Beschreibung | Generalisierbar? |
|---------|--------------------|---------|--------------|--------------------|

## Gesamtbewertung

- Signal-Qualität für dieses Repo: [trusted / needs_review / unsafe]
- Stärkste Signale: [Liste]
- Schwächste Signale: [Liste]
- Empfohlener nächster Schritt: [context-eval / Issues melden / keine Aktion]

## Prioritäre Verbesserungen für drift

1. [...]
2. [...]
3. [...]
```

## Entscheidungsregel

Wenn du die Architekturentscheidung des Repos nicht sicher beurteilen kannst, klassifiziere als `uncertain` — nicht als FP. Nur gesicherte Fehlklassifikationen erzeugen Issues.

## GitHub-Issue-Erstellung

Am Ende des Workflows GitHub-Issues auf `mick-gsk/drift` erstellen gemäß `.github/prompts/_partials/issue-filing-external.md`.

**Prompt-Kürzel für Titel:** `finding-audit`

### Issues erstellen für

- Signale mit `unsafe`-Vertrauensstufe und generalisierbarem FP-Pattern
- Systematische Severity-Fehlkalibrierung (gleiche Richtung über mehrere Findings)
- Cross-Validation-`contradiction` zwischen scan und analyze
- FN für offensichtliche Architekturprobleme (die jeder Code-Reviewer erkennen würde)

### Keine Issues erstellen für

- Repo-spezifische Eigenheiten, die drift nicht kennen kann
- Oracle-Fälle mit `uncertain`-Klassifikation
- Einzelne FP ohne erkennbares Pattern (Zufall oder Oracle-Schwäche)
- Severity-Abweichungen um eine Stufe (subjektiv)
