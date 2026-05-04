# Contract: Migration Boundary and Completion

## Contract Scope
Dieser Vertrag definiert die nachpruefbaren Bedingungen fuer den Abschluss der Monorepo-Migration von Legacy-Strukturen zu Capability-Paketen.

## External Interface Expectations

### 1. Contributor-Navigation Contract
- Given ein Beitragender sucht eine aktive Drift-Implementierung,
- When der Codebaum durchsucht wird,
- Then liegen kanonische Implementierungen in `packages/drift-*` und nicht als aktive Quelle unter `src/drift`.

### 2. Internal Import Contract
- Given ein interner Drift-Import fuer produktive Logik,
- When statische Analyse/Tests laufen,
- Then zeigt der Import auf einen kanonischen Capability-Paketpfad.

### 3. Quality Gate Contract
- Given der Migrationsabschluss soll festgestellt werden,
- When der definierte Gate-Lauf ausgefuehrt wird,
- Then sind Lint, Typecheck, Tests und projektspezifische Gate-Pruefungen erfolgreich.

### 4. Documentation Contract
- Given die Migration ist als abgeschlossen markiert,
- When Contributor Architektur- und Developer-Dokumentation lesen,
- Then sind Paketgrenzen, kanonische Pfade und Abschlusskriterien eindeutig dokumentiert.

## Non-Goals
- Keine Erweiterung fachlicher Drift-Features.
- Keine Umgestaltung bestehender Produktlogik ohne direkten Migrationsbezug.

## Verification Evidence
- Such-/Audit-Ergebnisse fuer verbliebene Legacy-Pfade.
- Gate-Lauf-Resultate fuer Qualitaets- und Compliance-Pruefungen.
- Dokumentations-Diffs mit aktualisierten Architekturgrenzen.
