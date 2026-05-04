# Research: Human Decision Cockpit

**Phase 0 Output** | Feature 006 | 2026-05-01

## R-001: Decision Status Semantik

**Decision**: Das Cockpit nutzt drei exklusive Status mit festen Schwellen je Status (`go`, `go_with_guardrails`, `no_go`) plus harter Override-Regel: unzureichende Evidenz erzwingt `no_go` unabhaengig vom numerischen Score.

**Rationale**: Die Clarifications verlangen deterministische Schwellen und genau einen Status pro PR. Harte Evidenz-Guard verhindert unsichere Freigaben.

**Alternatives considered**:
- Dynamische Schwellen pro Repo: schwer vergleichbar und nicht baseline-stabil.
- Ein globale Schwelle: zu grob fuer Guardrails-Szenarien.

## R-002: Minimal Safe Change Set Berechnung

**Decision**: V1 verwendet eine deterministische Greedy-Heuristik ueber priorisierte Risikotreiber (impact-descending) und waehlt den kleinsten Maßnahmen-Satz, der unter die Zielschwelle bringt.

**Rationale**: Erklaerbar, schnell testbar und ausreichend fuer V1; liefert gleichzeitig erwartetes Risiko-Delta und Score-Delta.

**Alternatives considered**:
- Exakte kombinatorische Optimierung: hoehere Komplexitaet, in V1 nicht noetig.
- Nur manuelle Vorschlaege: verletzt FR-003/FR-004.

## R-003: Ledger-Konsistenz und Konflikte

**Decision**: Ledger-Updates nutzen optimistic locking (`version` Feld); bei stale version wird ein expliziter Konflikt zur Aufloesung zurueckgegeben.

**Rationale**: Erfuellt FR-015 und verhindert stille Ueberschreibungen.

**Alternatives considered**:
- Last-write-wins: nicht auditierbar.
- Global lock: zu restriktiv fuer parallele Maintainer-Workflows.

## R-004: Human Override Governance

**Decision**: Menschliche Uebersteuerung ist erlaubt, aber nur mit Pflichtfeldern `override_reason`, `decision_actor`, `decided_at`.

**Rationale**: Erfuellt FR-013 und macht spaetere Outcome-Analyse belastbar.

**Alternatives considered**:
- Freie Uebersteuerung ohne Begruendung: schwache Governance.
- Keine Uebersteuerung: unpraktisch fuer Maintainer-Verantwortung.

## R-005: Outcome Tracking Modell

**Decision**: 7/30-Tage-Outcomes werden als statusbehaftete Subobjekte modelliert (`pending|captured|not_available`) und spaeter denselben Ledger-Eintrag erweitert.

**Rationale**: Expliziter Pending-Status erfuellt Clarification und verhindert Fehlinterpretation als neutral.

**Alternatives considered**:
- Fehlende Outcomes als null/leer: semantisch unklar.
- Separate Outcome-Tabelle ohne Ledger-Link: schwache Rueckverfolgbarkeit.

## R-006: UI-Integrationsstrategie

**Decision**: UI wird als eigener Cockpit-Bereich im bestehenden `playground` realisiert und konsumiert die Cockpit-API-Artefakte.

**Rationale**: Wiederverwendung der vorhandenen Vite/React Toolchain im Repo reduziert Einfuehrungsaufwand.

**Alternatives considered**:
- Komplett neue Frontend-App im Repo-Root: mehr Build-/CI-Oberflaeche ohne V1-Mehrwert.
- Nur Rich-Ausgabe: erfuellt Produktziel "Web App" nicht.
