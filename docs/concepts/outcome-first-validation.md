# Outcome-First Validation (Agent Productivity)

Status: proposed
Owner: maintainers
Updated: 2026-05-01

## Problem Statement

Drift reduziert heute oft Findings und Drift-Score, aber der reale Nutzen in
Agenten-Workflows bleibt fuer Nutzer haeufig unsichtbar.

Wenn Architektur-Fixes keinen messbaren Effekt auf Agentenarbeit zeigen,
wirken sie wie optionales Cleanup statt wie Produktivitaetshebel.

## Ziel

Drift-Erfolg wird primaer ueber reale Workflow-Outcomes bewertet:

- weniger Schritte bis zum Ziel
- weniger Rework (Rueckgaengigmachen, Ersatz-Edits, Sackgassen)
- hoehere First-pass-Erfolgsquote
- keine steigende Defect-Rate nach Abschluss

Score/Finding-Reduktion bleibt Diagnostik, ist aber kein alleiniger
Nutzenbeweis.

## 14-Day Validation Protocol

### Scope

- Zeitraum: 14 Kalendertage
- Stichprobe: reale Agenten-Tasks aus normalem Workflow
- Gruppen:
  - A = Drift-informierte Taskbearbeitung
  - B = Taskbearbeitung ohne Drift-Eingriff

### Core Metrics

- median_steps_to_completion
- rework_rate
- first_pass_success_rate
- post_completion_defect_rate

### Guardrails

- Defect-Rate darf gegenueber Baseline nicht steigen.
- Optionales Cleanup ohne Outcome-Hypothese wird nicht als Erfolg gezaehlt.

### Go/No-Go Thresholds

Go, wenn mindestens zwei Kernmetriken klar verbessern und keine Guardrail verletzt ist:

- steps: mindestens 25% besser
- rework: mindestens 30% besser
- first_pass: mindestens 15 Prozentpunkte besser
- defects: nicht schlechter als Baseline

No-Go, wenn nach 14 Tagen keine robuste Verbesserung sichtbar ist oder
die Defect-Rate steigt.

## Interpretation Rules

- "Weniger Findings" und "niedrigerer Score" sind Proxy-Signale.
- Proxy-Signale duerfen nur zusammen mit Outcome-Effekten als Erfolg gelten.
- Eingriffe ohne plausiblen Einfluss auf Schritte/Rework sind nachrangig.

## Deliverables at Day 14

- kompakte Vorher/Nachher-Tabelle fuer alle vier Kernmetriken
- Liste wirksamer Drift-Eingriffe (mit beobachtetem Effekt)
- Liste nicht-wirksamer Drift-Eingriffe (depriorisieren oder entfernen)
- Produktentscheidung: continue, narrow, or pivot

## Out of Scope

- keine neuen Signale nur fuer diesen Test
- keine neuen CLI-Oberflaechen als Voraussetzung
- kein Umbau der Instructions

## Notes

Dieses Dokument ist ein Validierungsrahmen fuer Produktentscheidungen.
Es ersetzt keine POLICY-Regeln und keine Push-Gates.
