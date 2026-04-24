# Controlled Rollout

## Phase 1: Conservative Hybrid

- Auto-Run nur bei `priority >= 10`
- harte Safety-Grenzen aktiv
- jede Block-Entscheidung begruendet reporten

## Phase 2: Balanced Hybrid

- Auto-Run bei `priority >= 8`
- gleiche Safety-Grenzen
- Fokus auf stabile False-Automation-Rate

## Phase 3: Expanded Hybrid

- optional `priority >= 7`, nur bei stabiler Historie ohne Safety-Verletzung
- regelmaessige Nachjustierung der Kandidatengewichte

## Monitoring-Metriken

- Anzahl automatisch ausgefuehrter Safe-Aktionen
- Anzahl blockierter Aktionen (nach Block-Grund)
- Anteil manueller Freigaben
- geschaetzte eingesparte manuelle Schritte
- Safety-Inzidenzen (muss 0 bleiben)

## Rollback-Kriterium

Sofort konservativ zurueck auf Phase 1, wenn:

- Safety-Inzidenz > 0
- wiederholte Fehltrigger mit hoher Auswirkung auftreten
- deterministisches Verhalten nicht mehr gegeben ist
