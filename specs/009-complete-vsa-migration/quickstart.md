# Quickstart: Complete VSA Migration

## Goal
Monorepo-Migrationsabschluss herstellen: `src/drift` ist keine aktive Implementierungsquelle mehr; Capability-Pakete sind kanonisch.

## Preconditions
- Entwicklungsumgebung ist eingerichtet.
- Projektabhaengigkeiten sind synchronisiert.
- Feature-Spec und Plan sind vorhanden.

## Steps

1. Baseline erfassen
- Aktuelle Legacy-Pfade unter `src/drift` inventarisieren.
- Aktive Implementierungs- und Importabhaengigkeiten dokumentieren.

2. Zielzuordnung festlegen
- Fuer jede verbleibende Legacy-Capability den kanonischen Zielpfad in `packages/drift-*` bestimmen.
- Importnormalisierungsmatrix erstellen (source -> target).

3. Migration ausfuehren
- Legacy-Implementierungsreste entfernen oder neutralisieren.
- Interne Importe auf kanonische Paketpfade umstellen.
- Oeffentliche API-Vertraege stabil halten und regressionssicher pruefen.

4. Verifikation durchfuehren
- Lint, Typecheck und relevante Test-Suiten ausfuehren.
- Projektspezifische Gates fuer Migrationsabschluss laufen lassen.
- Legacy-Pfad-Audit wiederholen und Null-Restbestand bestaetigen.

5. Dokumentation finalisieren
- Architektur- und Contributor-Doku auf neue Paketgrenzen aktualisieren.
- Abschlussstatus mit klaren Kriterien festhalten.

## Expected Result
- Kanonische Drift-Implementierung liegt ausschliesslich in Capability-Paketen.
- Kein produktiver Pfad haengt von `src/drift` ab.
- Qualitaets- und Gate-Pruefungen passieren im Zielzustand.
