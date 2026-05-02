# Research: Complete VSA Migration

## Decision 1: Capability-Pakete sind alleinige kanonische Implementierungsquelle
- Decision: Produktive Drift-Implementierungen werden ausschliesslich in `packages/drift-*` Capability-Paketen gefuehrt; `src/drift` bleibt nicht als aktive Implementierungsflaeche bestehen.
- Rationale: Ein klarer kanonischer Code-Ort reduziert Navigationsfehler, verhindert Doppelwartung und verbessert Agenten-Kontextqualitaet.
- Alternatives considered: Dauerhafte Dual-Struktur mit parallelen Legacy-Pfaden; verworfen wegen hoher Verwechslungs- und Regressionsgefahr.

## Decision 2: Migration erfolgt ueber API-stabile Importnormalisierung
- Decision: Interne Importe werden auf kanonische Paketpfade normalisiert, waehrend oeffentliche Nutzungsvertraege explizit geprueft werden.
- Rationale: So bleibt Verhalten stabil, aber interne Implementierung wird konsequent auf VSA-Slices ausgerichtet.
- Alternatives considered: Big-Bang-Umstellung ohne Zwischenvalidierung; verworfen wegen hoher Ausfallwahrscheinlichkeit bei grossen Codebasen.

## Decision 3: Verifikation als Gate-Buendel statt Einzeltests
- Decision: Abschlusskriterium ist ein kombinierter Gate-Lauf (Lint, Typecheck, Tests, projektspezifische Gate-Checks) plus Import-/Pfad-Audits.
- Rationale: Die Migration ist architekturweit; nur zusammengesetzte Verifikation belegt den sicheren Zielzustand.
- Alternatives considered: Nur selektive Smoke-Tests; verworfen, da nicht ausreichend fuer Migrationsabschluss.

## Decision 4: Architektur- und Contributor-Doku sind Teil des Deliverables
- Decision: Dokumentation von Paketgrenzen, kanonischen Pfaden und Migrationsabschluss wird als Pflichtbestandteil der Umsetzung gefuehrt.
- Rationale: Ohne klare Doku kehrt Legacy-Nutzung schnell zurueck und verwischt wieder die Zustandsgrenzen.
- Alternatives considered: Doku nachgelagert aktualisieren; verworfen, da Onboarding-Effekt sonst verzögert und fehleranfällig bleibt.

## Decision 5: Abschluss als expliziter Repository-Zustand
- Decision: Der Migrationszyklus gilt nur dann als abgeschlossen, wenn kein aktiver Produktionspfad mehr von `src/drift` abhaengt und dieser Zustand dokumentiert und testbar nachgewiesen ist.
- Rationale: Ein expliziter Abschlussstatus verhindert schleichende Rueckfaelle in Hybrid-Architekturen.
- Alternatives considered: Informeller Abschluss ohne maschinenpruefbare Kriterien; verworfen wegen fehlender Nachhaltigkeit.
