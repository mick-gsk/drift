# Feature Specification: Complete VSA Migration

**Feature Branch**: `[feat/adr100-phase7a-cleanup]`  
**Created**: 2026-05-02  
**Status**: Draft  
**Input**: User description: "src/drift vollstaendig durch packages/drift-*-Capability-Pakete ersetzen und den Monorepo-Migrationszyklus abschliessen. Nutzen: vollstaendige VSA im Monorepo, klare Paketgrenzen, weniger Verwirrung fuer neue Contributor:innen, bessere Agent-Kontext-Effizienz."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Konsistente Paketnavigation (Priority: P1)

Als Contributor moechte ich jede Drift-Funktionalitaet nur noch in klar abgegrenzten Capability-Paketen finden, damit ich ohne doppelte Pfade und Alias-Verwirrung arbeiten kann.

**Why this priority**: Doppelstrukturen zwischen `src/drift` und Capability-Paketen verursachen die groesste Reibung bei Aenderungen, Reviews und Onboarding.

**Independent Test**: Kann unabhaengig getestet werden, indem ein Contributor eine typische Aenderungsaufgabe (z. B. Kommando, Signal oder Session-Workflow) ohne Rueckgriff auf `src/drift` lokalisiert und durchfuehrt.

**Acceptance Scenarios**:

1. **Given** ein frischer Clone, **When** ein Contributor die relevanten Module fuer eine Feature-Aenderung sucht, **Then** sind die kanonischen Implementierungen ausschliesslich in den vorgesehenen Capability-Paketen auffindbar.
2. **Given** eine bestehende Referenz auf Legacy-Pfade, **When** die Dokumentation und Architekturuebersicht konsultiert wird, **Then** ist eindeutig ersichtlich, welche Paketpfade verbindlich sind und dass `src/drift` nicht mehr als aktive Implementierungsflaeche dient.

---

### User Story 2 - Verlaesslicher Agenten-Workflow (Priority: P2)

Als Coding-Agent moechte ich bei Aenderungen nur eine kanonische Code-Quelle je Slice sehen, damit Kontextsuche, Diff-Analyse und Fix-Loops ohne Migrationsartefakt-Rauschen funktionieren.

**Why this priority**: Reduzierter Suchraum und eindeutige Ownership verbessern die Genauigkeit agentischer Entscheidungen.

**Independent Test**: Kann unabhaengig getestet werden, indem ein Agent mehrere representative Aufgaben in unterschiedlichen Slices bearbeitet und dabei keine Legacy-Implementierungen unter `src/drift` mehr als aktive Quelle verwendet.

**Acceptance Scenarios**:

1. **Given** eine agentische Suche nach aenderungsrelevanten Symbolen, **When** die erste Treffermenge ausgewertet wird, **Then** zeigen Treffer auf Capability-Paketpfade statt auf Legacy-Implementierungen in `src/drift`.
2. **Given** ein agentischer Fix-Loop mit Verifikation, **When** Patches erstellt und validiert werden, **Then** entstehen keine Rueckfaelle durch parallele Legacy-Implementierungen.

---

### User Story 3 - Niedrigere Onboarding-Huerde (Priority: P3)

Als neuer Beitragender moechte ich die Architektur in einem Durchgang verstehen, damit ich schneller produktive Beitraege liefern kann.

**Why this priority**: Klarheit in Struktur und Verantwortlichkeiten senkt Einstiegskosten und reduziert Rueckfragen.

**Independent Test**: Kann unabhaengig getestet werden, indem ein neuer Beitragender ein Onboarding-Szenario mit Architektur- und Developer-Dokumentation durchlaeuft und anschliessend eine kleine Aenderung korrekt in einem Capability-Paket umsetzt.

**Acceptance Scenarios**:

1. **Given** Onboarding-Dokumentation und Codebaum, **When** ein neuer Beitragender eine erste Aenderung vorbereitet, **Then** kann er das richtige Capability-Paket ohne Nachfragen identifizieren.

### Edge Cases

- Wie wird mit verbliebenen Imports in externen Skripten oder Tests umgegangen, die noch auf Legacy-Pfade zeigen?
- Wie wird sichergestellt, dass Build-, Lint-, Test- und Analyse-Workflows nicht implizit von `src/drift`-Resten abhaengen?
- Was passiert, wenn einzelne Slices bereits migriert sind, andere aber noch Legacy-Referenzen enthalten?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Das System MUSS fuer jede Drift-Capability genau einen kanonischen Implementierungspfad in den vorgesehenen Capability-Paketen definieren.
- **FR-002**: Das System MUSS alle aktiven Implementierungsreste unter `src/drift` entfernen oder so aufloesen, dass `src/drift` nicht mehr als produktive Implementierungsquelle genutzt wird.
- **FR-003**: Das System MUSS bestehende interne Importpfade auf die kanonischen Capability-Paketpfade angleichen, sodass keine funktionalen Abhaengigkeiten auf Legacy-Pfade verbleiben.
- **FR-004**: Das System MUSS Architektur- und Entwicklerdokumentation aktualisieren, damit Contributor den neuen Paketgrenzen eindeutig folgen koennen.
- **FR-005**: Das System MUSS nach der Migration den bestehenden Qualitaets-Gates entsprechen, inklusive Build, Typpruefung, Tests und projektspezifischen Gate-Pruefungen.
- **FR-006**: Das System MUSS den Abschluss der Monorepo-Migration als eindeutigen Zustand dokumentieren, damit Folgearbeiten nicht erneut Legacy-Strukturen einfuehren.

### Key Entities *(include if feature involves data)*

- **Capability-Paket**: Fachliche Vertikalscheibe mit klarer Ownership fuer Modelle, Logik und oeffentliche API eines Drift-Teilbereichs.
- **Legacy-Pfad**: Historischer Pfad unter `src/drift`, der waehrend der Migration als Kompatibilitaets- oder Uebergangsflaeche gedient hat.
- **Migrationsabschlussstatus**: Nachweisbarer Projektzustand, in dem nur noch die Capability-Pakete als aktive Implementierungsquellen gelten.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% der aktiven Drift-Implementierungen liegen in den definierten Capability-Paketen; `src/drift` wird nicht mehr als produktive Implementierungsflaeche verwendet.
- **SC-002**: 100% der geprueften internen Referenzen fuer aktive Funktionalitaet zeigen auf kanonische Capability-Paketpfade.
- **SC-003**: Mindestens 90% der neuen Contributor koennen in einem standardisierten Onboarding-Test mit mindestens 10 Durchlaeufen das korrekte Zielpaket fuer eine Beispielaenderung ohne Zusatzhilfe im ersten Versuch bestimmen.
- **SC-004**: Alle verbindlichen Qualitaets- und Gate-Pruefungen bestehen im Zielzustand ohne migrationsbedingte Sonderbehandlung.

## Assumptions

- Die bestehenden Capability-Pakete decken fachlich bereits alle benoetigten Drift-Bereiche ab und muessen nur final konsolidiert werden.
- Externe Integrationen duerfen bei Bedarf ueber klar dokumentierte Kompatibilitaetspfade uebergangsweise stabil gehalten werden, ohne `src/drift` als aktive Implementierungsquelle fortzufuehren.
- Die Umstellung erfolgt so, dass laufende Contributor-Arbeit nicht durch grossflaechige, ungeplante Nebenmigrationen blockiert wird.
- Die Architektur- und Entwicklungsdokumentation ist Teil des Lieferumfangs und nicht nur ein nachgelagerter Schritt.
