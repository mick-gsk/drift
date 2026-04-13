---
id: ADR-067
status: proposed
date: 2026-04-13
supersedes:
---

# ADR-067: Effektivitätsstudie für `drift brief` (A/B-Experiment)

## Kontext

`drift brief` generiert aufgabenbezogene Guardrails und leitet diese als Prompt-Constraints in Agent-Prompts ein, bevor ein Agent Code schreibt. Das Feature wurde in v2.3.0 eingeführt. Die vorhandene Evidenz beschränkt sich auf:

- Unit-Tests, die Output-Korrektheit der Guardrail-Generierung verifizieren (`tests/test_brief.py`, `tests/test_scope_resolver.py`)
- Signal-Qualitätsmetriken für die zugrunde liegenden Signale (77 % Präzision / 86 % Recall — v0.5-Modell, einrater, nicht auf das aktuelle v2.x-Modell rückvalidiert; Quelle: `docs/STUDY.md`)

**Was vollständig fehlt:** ein unabhängiger Nachweis, dass `drift brief`-Constraints den Downstream-Fehlerrate des Agents messbar reduzieren. Es gibt weder A/B-Daten noch kontrollierte Ableitungskette von "Guardrail ausgegeben" zu "Layer-Violation oder Regression eingespart".

Der Claim in `README.md` ("drift brief injects structural guardrails *before* the agent writes code") und in `docs/guides/agent-workflow.md` ist daher produktseitig plausibel begründet, aber empirisch unbelegt.

## Entscheidung

### Was zu tun ist

Durchführung eines kontrollierten Experiments mit folgendem Minimalaufbau:

1. **Corpus:** 10–20 reale Tasks aus öffentlichen Python-Repositories (Bugfixes, kleine Features, Refactorings), die mindestens eine Drift-Kategorie der Ziel-Signale berühren (z. B. AAV, DIA, HSC, MDS).
2. **Treatments:**
   - `control`: Agent erhält Task-Beschreibung + Codebase-Ausschnitt, kein `drift brief`-Output
   - `treatment`: Agent erhält dasselbe + vollständigen `drift brief --format json`-Output als System-Prompt-Prefix
3. **Agent:** Gleiche Modell-/Temperaturkonfiguration in beiden Gruppen; zufällige Zuweisung pro Task.
4. **Abhängige Variablen (mindestens zwei):**
   - Rate an neu eingeführten Drift-Findings im erzeugten Diff (gemessen mit `drift diff`)
   - Rate an Task-Korrektheit (unabhängige Beurteilung durch zweiten Reviewer oder automatische Test-Suite)
5. **Blindheit:** Bewerter soll nicht wissen, welche Gruppe ein Diff erzeugt hat.
6. **Statistik:** Minimum n=20 Tasks pro Gruppe; exakter Fisher-Test oder Mann-Whitney U bei kleiner Stichprobe; Effektgröße Cohen's d.
7. **Ergebnis-Artefakt:** `benchmark_results/drift_brief_ab_study.json` mit rohen Task-Ergebnissen, Gruppen-Zuweisung und aggregierten Metriken.

### Was explizit nicht getan wird

- Keine Änderung an `drift brief`-Implementierung oder -Output-Format vor Abschluss der Studie.
- Keine Anpassung der Guardrail-Inhalte, um die Studie zu "optimieren" (Confirmation Bias).
- Kein Update des `README.md`-Claims, bevor Ergebnisse vorliegen.
- Kein Einsatz des Studien-Designs, um `drift brief` durch Nachsteuerung zur Signifikanz zu zwingen.

## Begründung

- **Kausalerkenntnis statt Plausibilität:** Structural-Context-Injection ist ein bekannter Wirkmechanismus in Prompt-Engineering, aber "bekannt plausibel" ≠ "gemessen wirksam" für diesen spezifischen Output-Typ.
- **Claim-Hygiene:** Ein Produkt, das Präzisions- und Recall-Ansprüche transparent dokumentiert (`docs/STUDY.md`, Policy §13), darf beim zentralen Nutzwesen-Claim keine Ausnahme machen.
- **Falsifizierbarkeit:** Das Experiment kann `drift brief` widerlegen. Wenn es keinen messbaren Effekt gibt, ist das ein valides Signal für Redesign oder Scope-Einschränkung — wertvoller als ein unbelegter positiver Claim.
- **Alternativen verworfen:**
  - *Nur Survey-Feedback:* zu subjektiv, keine kontrollierten Bedingungen
  - *Proxy-Metriken aus bestehenden Runs:* kein Control-Arm vorhanden
  - *Warten auf mehr Nutzerdaten:* unbegrenzt aufschiebbares Ziel, keine Entscheidungsgrundlage

## Konsequenzen

- Bis Abschluss der Studie bleibt der `README.md`-Claim unverändert, aber in `docs/STUDY.md` wird eine explizite **Evidenzlücken-Notiz** ergänzt: Brief-Effekt ist plausibler Mechanismus, nicht gemessener Effekt.
- Bei positivem Ergebnis (p < 0.05, d ≥ 0.3): Claim in `README.md` mit Verweis auf Studie stärken; Guardrail-Qualität als KPI in `benchmark_results/kpi_snapshot.json` verankern.
- Bei Null-Ergebnis: Claim abschwächen oder auf "ergonomischer Kontext für Agenten" reduzieren; ggf. Guardrail-Inhalte grundlegend überarbeiten.
- Regressionsrisiko: keines für bestehende Signale oder Output-Formate.

## Validierung

Studie gilt als abgeschlossen, wenn:
- `benchmark_results/drift_brief_ab_study.json` existiert und den Minimalaufbau (n≥20/Gruppe, zwei primäre Outcomes, statistische Kennzahlen) erfüllt
- Ergebnis-Status in diesem ADR auf `accepted` (Wirkung nachgewiesen) oder `rejected` (kein messbarer Effekt) gesetzt wurde

Policy §10 Lernzyklus-Ergebnis: **zurückgestellt** — Studie noch nicht durchgeführt.
