# Bewertungs-Taxonomie (Shared Reference)

> **Single Source of Truth** — Alle Prompts in `.github/prompts/` verwenden ausschließlich diese Labels.
> Wenn ein Prompt abweichende Labels nutzt, ist diese Datei maßgeblich.

## Ergebnis-Bewertung (pro Schritt / pro Kommando)

| Label | Bedeutung |
|-------|-----------|
| `pass` | Nächster Schritt ist klar, Evidenz reicht aus, Agent kann sicher fortfahren |
| `review` | Teilweise nützlich, aber fehlende Daten, Priorisierung oder Entscheidungsgrundlage — Agent braucht zusätzliche Prüfung |
| `fail` | Irreführend, blockiert oder lenkt den Agent in eine falsche Richtung |

## Abdeckungs-Status (pro Kommando / Testfall)

| Label | Bedeutung |
|-------|-----------|
| `tested` | Vollständig ausgeführt und bewertet |
| `skipped` | Begründet übersprungen (Grund dokumentiert) |
| `blocked` | Ausführung nicht möglich (Ursache dokumentiert) |

## Risiko-Level (pro Dimension / pro Finding)

| Label | Bedeutung |
|-------|-----------|
| `low` | Kein oder minimaler Einfluss auf Entscheidungssicherheit |
| `medium` | Spürbarer Einfluss, aber kein Workflow-Blocker |
| `high` | Erheblicher Einfluss auf Entscheidungssicherheit oder Agent-Workflow |
| `critical` | Blockiert den Workflow oder erzeugt falsche Entscheidungen |

## Signal-Vertrauensstufe (pro Signal)

| Label | Bedeutung |
|-------|-----------|
| `trusted` | Precision ≥ 70%, Actionability ≥ 3, Agent kann blindlings handeln |
| `needs_review` | Precision 50–70% oder Actionability < 3, Maintainer-Prüfung nötig |
| `unsafe` | Precision < 50%, Signal erzeugt mehr Fehlentscheidungen als korrekte |

## Actionability-Score (1–4, pro Signal)

| Score | Bedeutung | Akzeptabel? |
|-------|-----------|-------------|
| `1 automated` | Fix ist mechanisch ableitbar, Agent kann direkt handeln | ✅ Ja |
| `2 guided` | Agent kann handeln, braucht aber expliciten Fix-Plan | ✅ Ja |
| `3 human-review` | Signal plausibel, aber Fix-Entscheidung braucht Maintainer | ⚠️ Bedingt |
| `4 blocked` | Keine sichere nächste Aktion möglich | ❌ Nein |

Schwelle für Produktionseinsatz: **Score ≤ 2** = Agent-tauglich, **Score 3** = nur mit Maintainer-Freigabe.

## Discoverability-Scale (für Recovery-Pfade)

| Label | Bedeutung | Agent-tauglich? |
|-------|-----------|-----------------|
| `explicit` | Tool benennt direkt die Recovery-Aktion | ✅ Ja |
| `hinted` | Genug Hinweise, um Recovery sicher abzuleiten | ✅ Ja |
| `pattern-match` | Nur erfahrene User finden den Pfad | ❌ Nein |
| `dark` | Kein Hinweis; nur Trial-and-Error | ❌ Nein |

## Idempotenz-Klassifikation (für CI-Stabilität)

| Label | Bedeutung | CI-tauglich? |
|-------|-----------|-------------|
| `stable` | Keine Differenz außer Timestamps/Run-IDs | ✅ Ja |
| `ordering-unstable` | Gleiche Findings, aber instabile Reihenfolge | ⚠️ Bedingt |
| `content-unstable` | Unterschiedliche Findings ohne Codeänderung — Product-Bug | ❌ Nein |

## Cross-Validation-Klassifikation (scan vs. analyze Konsistenz)

| Label | Bedeutung |
|-------|-----------|
| `metadata-only` | Nur kosmetisch, kein Entscheidungsimpact |
| `priority-shift` | Severity/Ranking unterscheiden sich, kann Agent fehlleiten |
| `contradiction` | Inhaltlich gegensätzliche Aussage — als `unsafe` bewerten |
