# Feature Specification: CLI Load Reduction

**Feature Branch**: `010-before-specify-hook`  
**Created**: 2026-05-02  
**Status**: Draft  
**Input**: User description: "Vorhaben: CLI Cognitive Load Reduction. Das drift CLI exponiert aktuell 48 flache Top-Level-Commands. Fuer neue Nutzer ist drift --help damit unlesbar; der Einstieg scheitert an Orientierungslosigkeit."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Schneller Einstieg ueber klares Help (Priority: P1)

Neue Nutzer wollen in den ersten Minuten verstehen, womit sie anfangen sollen, ohne durch eine lange, unstrukturierte Befehlsliste zu scrollen.

**Why this priority**: Der erste Kontakt mit `drift --help` entscheidet, ob Nutzer das Tool weiterverwenden oder abbrechen.

**Independent Test**: Kann unabhaengig getestet werden, indem Erstnutzer nur mit `drift --help` und den Einstiegsbefehlen eine erste Analyse erfolgreich starten.

**Acceptance Scenarios**:

1. **Given** ein neuer Nutzer ohne Drift-Vorkenntnisse, **When** der Nutzer `drift --help` aufruft, **Then** erkennt der Nutzer klar die empfohlenen Einstiegswege und ihren Zweck.
2. **Given** ein neuer Nutzer mit konkretem Ziel, **When** der Nutzer den Help-Text liest, **Then** findet der Nutzer den passenden Befehlspfad in unter 60 Sekunden.

---

### User Story 2 - Zielorientierte Navigation statt Befehlssuche (Priority: P2)

Fortgeschrittene Nutzer wollen von einem Ziel (z. B. Analyse, Reparatur, Reporting) aus navigieren und nicht jede Top-Level-Option einzeln pruefen.

**Why this priority**: Die Auffindbarkeit steigt, wenn das CLI nach Nutzungsintention statt alphabetischer Flut strukturiert ist.

**Independent Test**: Kann unabhaengig getestet werden, indem Nutzer typische Aufgaben ohne externe Dokumentation durch die Help-Navigation abschliessen.

**Acceptance Scenarios**:

1. **Given** ein Nutzer mit dem Ziel "Codebasis analysieren", **When** der Nutzer die Help-Ausgabe nutzt, **Then** gelangt der Nutzer direkt zu den relevanten Analyse-Kommandos ohne irrelevante Umwege.
2. **Given** ein Nutzer mit dem Ziel "Ergebnisse exportieren", **When** der Nutzer die Help-Ausgabe nutzt, **Then** findet der Nutzer die Export-Optionen in einer logisch passenden Kategorie.

---

### User Story 3 - Stabiler Betrieb fuer bestehende Workflows (Priority: P3)

Bestehende Nutzer wollen ihre etablierten Skripte und Kommandonutzung weiterverwenden koennen, waehrend neue Orientierungshilfen eingefuehrt werden.

**Why this priority**: Adoption scheitert, wenn die UX verbessert wird, aber bestehende Nutzungen regressieren.

**Independent Test**: Kann unabhaengig getestet werden, indem bekannte Kommandopfad-Aufrufe weiterhin erfolgreich ausfuehrbar sind und die neuen Orientierungshilfen parallel funktionieren.

**Acceptance Scenarios**:

1. **Given** ein bestehender Nutzer mit gespeichertem CLI-Workflow, **When** der Nutzer denselben Befehl aufruft, **Then** bleibt das erwartete Verhalten unveraendert.
2. **Given** ein bestehender Nutzer, **When** der Nutzer die neue Help-Ausgabe aufruft, **Then** erhaelt der Nutzer zusaetzliche Orientierung ohne Verlust bestehender Funktionalitaet.

### Edge Cases

- Was passiert, wenn Nutzer direkt nach einem konkreten Legacy-Befehl suchen, der nicht in den bevorzugten Einstiegswegen liegt?
- Wie wird verhindert, dass ein Nutzer durch mehrere gleich plausible Einstiegspfade wieder unklar orientiert ist?
- Wie verhaelt sich die Orientierung bei sehr schmalen Terminalbreiten, wenn weniger Inhalt gleichzeitig sichtbar ist?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Das System MUSS die CLI-Help-Ausgabe so strukturieren, dass Erstnutzer mindestens einen klaren "Start hier"-Pfad sehen.
- **FR-002**: Das System MUSS Befehle in fuer Nutzer verstaendliche Aufgabenbereiche gruppieren, statt nur als flache Gesamtliste zu praesentieren.
- **FR-003**: Das System MUSS pro Aufgabenbereich den Zweck in kurzer, nicht-technischer Sprache erklaeren.
- **FR-004**: Das System MUSS einen direkten Weg anbieten, von einer Aufgabenbeschreibung zum passenden Befehl zu gelangen.
- **FR-005**: Das System MUSS bestehende, bereits verwendete Befehlspfade weiterhin unterstuetzen.
- **FR-006**: Das System MUSS bei Help-Ausgaben die visuelle Ueberlast reduzieren, indem im initial sichtbaren Bereich maximal 3 Primaersektionen erscheinen (Start hier, Capability-Uebersicht, Naechster Schritt) und jede Primaersektion hoechstens 7 Zeilen umfasst.
- **FR-007**: Das System MUSS fuer Nutzer erkennbar machen, wie sie von einer globalen Uebersicht in detailliertere Hilfe wechseln.

### Key Entities *(include if feature involves data)*

- **Command Capability Area**: Ein nutzerorientierter Aufgabenbereich (z. B. analysieren, reparieren, berichten), der mehrere CLI-Befehle zusammenfasst.
- **Entry Path**: Ein empfohlener Startpfad fuer typische Nutzerziele mit kurzer Handlungsanleitung.
- **Help Section**: Ein klar abgegrenzter Teil der Hilfeausgabe mit Zweckbeschreibung, zugeordneten Befehlen und Navigationshinweisen.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Mindestens 85% neuer Nutzer identifizieren innerhalb von 60 Sekunden den passenden Einstiegsbefehl fuer eine vorgegebene Standardaufgabe.
- **SC-002**: Die durchschnittliche Zeit vom ersten `drift --help` bis zum erfolgreichen Start einer ersten Analyse sinkt um mindestens 40% gegenueber dem aktuellen Zustand.
- **SC-003**: Mindestens 90% der in internen Regressionstests abgedeckten bestehenden CLI-Aufrufe bleiben unveraendert erfolgreich.
- **SC-004**: Mindestens 80% der befragten Nutzer bewerten die Help-Navigation als "klar" oder "sehr klar".

## Assumptions

- Die primaere Schmerzstelle liegt in Orientierung und Informationsdichte, nicht in fehlenden Kernfunktionen.
- Nutzer kommen mit unterschiedlichen Erfahrungsniveaus; der Einstieg muss ohne Vorwissen funktionieren.
- Verbesserte Orientierung soll additive Fuehrung bieten und bestehende Nutzungspfade nicht entfernen.
- Der Schwerpunkt liegt auf CLI-internen Orientierungshilfen; externe Dokumentation bleibt ergaenzend, aber nicht Voraussetzung fuer den Einstieg.