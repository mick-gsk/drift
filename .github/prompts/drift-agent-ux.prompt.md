---
name: "Drift Agent UX"
agent: agent
description: "Bewertet Drift-CLI aus Agent-Perspektive: Auffindbarkeit, Feedback-Latenz, Fehlermeldungen, End-to-End-Konsistenz. Vergleicht Agent-UX mit menschlicher UX."
---

# Drift Agent UX

Du evaluierst die Drift-CLI aus der Perspektive eines Agent-Users. Dein Fokus liegt auf Auffindbarkeit, Latenz, Fehlernachrichten und konsistentem Verhalten über Kommandos hinweg.

> **Pflicht:** Vor Ausführung dieses Prompts das Drift Policy Gate durchlaufen
> (siehe `.github/prompts/_partials/konventionen.md` und `.github/instructions/drift-policy.instructions.md`).

## Relevante Referenzen

- **Instruction:** `.github/instructions/drift-policy.instructions.md`
- **Bewertungssystem:** `.github/prompts/_partials/bewertungs-taxonomie.md`
- **Issue-Filing:** `.github/prompts/_partials/issue-filing.md`
- **Verwandte Prompts:** `drift-agent-workflow-test.prompt.md` (CI-Realism), `drift-ci-gate.prompt.md` (Gate-Perspektive)
- **CLI-Implementierung:** `src/drift/commands/` (Click-CLI-Subcommands)

## Arbeitsmodus

- Interagiere als Agent: systematisch, breadth-first, exit-code-gesteuert.
- Beobachte und dokumentiere statt sofort zu bewerten.
- Erkläre die Kognition hinter jedem Urteil (z.B. „ein Mensch würde X tun, ein Agent bräuchte Y").
- Wenn ein Workflow abbricht, bestimme die günstigste Abbruchursache, nicht die schlimmste.
- Unterscheide Agent-UX-Probleme von allgemeinen CLI-Bugs.

## Ziel

Bestimme, ob ein Coding-Agent Drift installieren, erkunden, nutzen und auf Ergebnisse reagieren kann — ohne Vorwissen, ohne Dokumentationslektüre, mit reinen CLI-Signalen.

## Erfolgskriterien

Die Aufgabe ist erst abgeschlossen, wenn du beantworten kannst:
- Konnte der Agent alle relevanten Kommandos und Optionen entdecken (`--help`-Auffindbarkeit)?
- Sind Fehlermeldungen informativ genug, um autonomes Recovery zu leiten?
- Ist die CLI-Latenz akzeptabel für interaktive Agent-Schleifen?
- Sind Output-Formate über Kommandos und Läufe hinweg konsistent?

## Arbeitsregeln

- Dokumentiere jedes Kommando mit Exit-Code und Antwortzeit.
- Behandle Latenz > 15 Sekunden als agent-disruptiv; errechne Recovery-Möglichkeit (Timeout + Retry vs. Abbruch).
- Verwende `--help` als primäre Auffindbarkeitsquelle — nicht Dokumentation.
- Prüfe Output-Metadaten auf Konsistenz über Formate.
- Bewerte Fehlermeldungen auf Actionability für autonomes Recovery.
- Falls `--help` Optionen beschreibt, die im realen Output nicht sichtbar sind: dokumentiere die Diskrepanz.

## Bewertungs-Labels

Verwende ausschließlich Labels aus `.github/prompts/_partials/bewertungs-taxonomie.md`:

- **Ergebnis-Bewertung:** `pass` / `review` / `fail`
- **Risiko-Level:** `low` / `medium` / `high` / `critical`
- **Auffindbarkeits-Skala:** `self-explanatory` / `documented` / `hidden` / `misleading`
- **Actionability-Score:** `1 automated` / `2 guided` / `3 human-review` / `4 blocked`

## Artefakte

Erstelle Artefakte unter `work_artifacts/agent_ux_<YYYY-MM-DD>/`:

1. `discovery_log.md`
2. `latency_matrix.md`
3. `error_catalog.md`
4. `consistency_audit.md`
5. `agent_ux_report.md`

## Workflow

### Phase 0: Auffindbarkeit

Erkunde die CLI als Zero-Knowledge-Agent.

```bash
drift --help
drift --version
```

Für jedes Top-Level-Kommando:
```bash
drift <command> --help
```

**Auffindbarkeits-Bewertung pro Kommando:**

| Kommando | Sichtbar in `--help`? | Beschreibung verständlich ohne Kontext? | Optionen vollständig? | Auffindbarkeit |
|----------|----------------------|----------------------------------------|----------------------|----------------|
| | | | | `self-explanatory` / `documented` / `hidden` / `misleading` |

**Subcommand-Konventionen-Check:**
- Verwenden alle Kommandos konsistente Benennung? (z.B. `kebab-case` vs. `snake_case`)
- Haben gemeinsame Optionen (z.B. `--repo`, `--format`) konsistente Defaults?
- Gibt es Aliases oder undokumentierte Kurzformen?

### Phase 1: Latenz-Profiling

Für jedes Kommando die Ausführungszeit messen:

```bash
Measure-Command { drift <command> [args] } | Select-Object TotalMilliseconds
```

| Kommando | Args | Latenz (ms) | Bewertung | Anmerkung |
|----------|------|-------------|-----------|-----------|
| | | | | |

**Latenz-Klassifikation:**
- < 2s: `acceptable` — Agent kann synchron warten
- 2–15s: `tolerable` — Agent sollte Timeout-Handling implementieren
- > 15s: `disruptive` — Agent-Loop wird unterbrochen

**Bei disruptiver Latenz zusätzlich dokumentieren:**
- Gibt es eine leichtgewichtigere Alternative (z.B. `scan` statt `analyze`)?
- Unterstützt das Kommando `--max-findings` oder ähnliche Begrenzung?
- Ist Recovery nach Timeout möglich (identisches Ergebnis bei erneutem Lauf)?

### Phase 2: Fehler-Verhalten

Provoziere realistische Fehlerszenarien:

```bash
drift analyze --repo /nonexistent
drift analyze --format unknown_format
drift scan --max-findings -1
drift export-context --repo . --format nonexistent
```

Pro Fehlerfall dokumentieren:

| Fehlerszenario | Exit-Code | Fehlermeldung | Actionability (1-4) | Anmerkung |
|----------------|-----------|---------------|---------------------|-----------|
| | | | | |

**Fehler-Qualitätskriterien:**
1. Enthält die Nachricht den konkreten Parameterwert, der fehlschlug?
2. Schlägt die Nachricht eine Korrektur vor (z.B. gültige Werte auflisten)?
3. Unterscheidet der Exit-Code Konfigurationsfehler von Analyseproblemen?
4. Ist die Fehlermeldung maschinell parsbar (Prefix-Konvention oder JSON)?

### Phase 3: Output-Konsistenz

Vergleiche Output-Formate für identische Eingabe:

```bash
drift analyze --repo . --format json > results_json.json
drift analyze --repo . --format sarif > results_sarif.json
drift analyze --repo .
```

**Konsistenz-Audit pro Format-Paar:**

| Attribut | JSON | SARIF | Rich-Terminal | Konsistenz |
|----------|------|-------|---------------|------------|
| Anzahl Findings | | | | `metadata-only` / `priority-shift` / `contradiction` |
| Signal-IDs | | | | |
| Severity-Labels | | | | |
| Betroffene Dateien | | | | |
| Reihenfolge | | | | |

### Idempotenz-Check

Für JSON und SARIF: Zweimalige Ausführung, Ergebnisse diffen:

```bash
drift analyze --repo . --format json > run1.json
drift analyze --repo . --format json > run2.json
diff run1.json run2.json
```

Klassifikation: `stable` / `ordering-unstable` / `content-unstable`

### Phase 4: Help-zu-Output-Konsistenz

Für jedes Kommando, das `--help` Optionen dokumentiert:
- Teste jede dokumentierte Option
- Dokumentiere Diskrepanzen zwischen Beschreibung und Verhalten

| Kommando | Option | Dokumentiert als | Tatsächliches Verhalten | Konsistent? |
|----------|--------|-----------------|------------------------|-------------|

### Phase 5: End-to-End-Agent-Szenario

Simuliere einen vollständigen Agent-Workflow:

```
1. drift --help                          → Kommandos entdecken
2. drift analyze --repo . --format json  → Ergebnisse erhalten
3. Ergebnisse parsen, höchstes Risiko identifizieren
4. drift explain <signal>                → Signal verstehen
5. Fix-Entscheidung treffen
```

Fließt der Workflow ohne menschliches Eingreifen? Wo bricht er ab?

### Phase 6: Report erstellen

```markdown
# Drift Agent UX Report

**Datum:** <YYYY-MM-DD>
**drift-Version:** [VERSION]
**Plattform:** [OS/SHELL]

## UX Scorecard

| Dimension | Bewertung | Evidenz | Impact |
|-----------|-----------|---------|--------|
| Auffindbarkeit | | | |
| Latenz | | | |
| Fehlermeldungen | | | |
| Output-Konsistenz | | | |
| Help-Genauigkeit | | | |
| End-to-End-Flow | | | |

## Latenz-Matrix

[Tabelle aus Phase 1]

## Fehlerkatalog

[Tabelle aus Phase 2]

## Konsistenz-Befunde

[Tabelle aus Phase 3]

## Auffindbarkeits-Audit

[Tabellen aus Phase 0 + 4]

## Prioritäre Verbesserungen

1. [...]
2. [...]
3. [...]
```

## Entscheidungsregel

Wenn ein Agent einen Workflow nur mit Dokumentationslektüre abschließen kann, ist die CLI-UX unzureichend für Agent-Nutzung. CLI-Signale müssen für sich sprechen.

## GitHub-Issue-Erstellung

Am Ende des Workflows GitHub-Issues erstellen gemäß `.github/prompts/_partials/issue-filing.md`.

**Prompt-Kürzel für Titel:** `agent-ux`

### Issues erstellen für

- Exit-Codes, die autonomes Recovery verhindern
- Fehlermeldungen ohne Actionability (Score 3 oder 4)
- Latenz-Probleme, die Agent-Schleifen unterbrechen (> 15s ohne Recovery)
- Output-Inkonsistenzen zwischen Formaten (Klassifikation `contradiction`)
- Help-Output, der von tatsächlichem Verhalten abweicht

### Keine Issues erstellen für

- Subjektive Formatpräferenzen ohne Agent-Impact
- Lokale Umgebungseffekte auf Latenz (z.B. Antivirus)
- Duplikate bereits existierender Issues
