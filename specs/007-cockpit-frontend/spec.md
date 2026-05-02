# Feature Specification: Drift Cockpit Frontend

**Feature Branch**: `011-cockpit-frontend`  
**Created**: 2026-05-02  
**Status**: Draft  
**Input**: User description: "es fehlt ein Frontend für das drift cockpit"

## Clarifications

### Session 2026-05-02

- Q: Welcher App-Typ ist für das Cockpit Frontend vorgesehen? → A: Next.js / Static Export — eigenständige Web-App mit Static Export (SSR at build time only) und direkten PR-URL-Shares.
- Q: Wie wird ein PR im Cockpit identifiziert und navigiert? → A: GitHub PR-URL als Eingabe — Cockpit leitet weiter zu `/cockpit/[owner]/[repo]/[pr_number]`, wobei Repo-Owner und PR-Nummer automatisch aufgelöst werden.
- Q: Wie wird ein laufender Scan im Cockpit dargestellt? → A: Lade-Indikator mit automatischem Poll/Stream — Teilresultate werden schrittweise angezeigt; kein Blockieren der Ansicht.
- Q: Wie soll das Cockpit auf das Backend zugreifen? → A: REST API via konfigurierbarer Backend-URL (Umgebungsvariable `COCKPIT_API_URL`).
- Q: Wie soll das Deployment des Cockpit Frontends erfolgen? → A: `drift cockpit serve` bündelt das vorgebaute Frontend und liefert es als statische Assets aus.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PR-Entscheidungsstatus auf einen Blick (Priority: P1)

Als Maintainerin öffne ich das Cockpit für einen Pull Request und sehe sofort den aktuellen Decision Status (Go, Go with Guardrails oder No-Go), den Konfidenzwert und die Top-Risikotreiber — ohne dass ich weitere Werkzeuge öffnen muss.

**Why this priority**: Das ist der Kernnutzen des Cockpits. Ohne diese Ansicht hat das gesamte Frontend keinen Wert.

**Independent Test**: Kann vollständig getestet werden, indem die Cockpit-Startseite für einen PR den Status, den Konfidenzwert und mindestens einen Risikotreiber in unter 2 Sekunden anzeigt.

**Acceptance Scenarios**:

1. **Given** ein analysierter PR mit ausreichender Evidenz, **When** die Maintainerin die Cockpit-URL für diesen PR aufruft, **Then** sieht sie Status-Badge (Go/Go with Guardrails/No-Go), Konfidenzwert und priorisierte Top-Risikotreiber ohne Login-Schranke im initialen Viewport.
2. **Given** ein PR mit unzureichender Evidenz, **When** die Cockpit-Seite geladen wird, **Then** wird der Status explizit als No-Go mit Hinweis auf fehlende Evidenz dargestellt.
3. **Given** mehrere Risikotreiber, **When** die Übersicht angezeigt wird, **Then** sind die Risikotreiber nach absteigendem Einfluss geordnet; der stärkste Treiber ist visuell hervorgehoben.

---

### User Story 2 - Minimal-Safe-Plan einsehen und Guardrails verstehen (Priority: P1)

Als Maintainerin öffne ich für einen No-Go- oder Guardrails-PR die Liste der Minimal-Safe-Plans und sehe pro Plan das erwartete Risiko-Delta und Score-Delta sowie die konkreten Guardrail-Bedingungen, die vor Merge erfüllt sein müssen.

**Why this priority**: Ohne operativen Plan bleiben No-Go-Entscheidungen abstrakt und nicht umsetzbar.

**Independent Test**: Kann unabhängig getestet werden, indem ein PR mit Status No-Go mindestens eine Plan-Karte mit Delta-Werten und Guardrail-Checkliste anzeigt.

**Acceptance Scenarios**:

1. **Given** ein PR mit Status No-Go, **When** die Maintainerin auf den Minimal-Safe-Plan-Tab klickt, **Then** sieht sie mindestens eine Plan-Karte mit erwartetem Risiko-Delta, Score-Delta und mindestens einer prüfbaren Guardrail-Bedingung.
2. **Given** ein Plan mit mehreren Guardrails, **When** einzelne Bedingungen abgehakt werden, **Then** aktualisiert die Übersicht den Erfüllungsstatus, ohne dass die Seite neu lädt.
3. **Given** ein Guardrails-Status-Plan, **When** alle Bedingungen erfüllt sind, **Then** wird dem Nutzer eine visuelle Bestätigung gezeigt, dass der Plan vollständig abgearbeitet ist.

---

### User Story 3 - Accountability Graph für Risikocluster (Priority: P2)

Als Maintainerin wechsle ich in die Graph-Ansicht und sehe die PR-Änderungen nach Risikoclustern gruppiert. Ich erkenne auf einen Blick, welcher Cluster den größten Anteil am Entscheidungsstatus trägt.

**Why this priority**: Die Cluster-Sicht erhöht die Nachvollziehbarkeit von Entscheidungen und vereinfacht die Kommunikation konkreter Guardrails.

**Independent Test**: Kann unabhängig getestet werden, indem eine Graph-Ansicht Cluster mit Risikoanteil darstellt, ohne dass Ledger oder Entscheidungsformular benötigt wird.

**Acceptance Scenarios**:

1. **Given** ein PR mit mehreren thematischen Änderungspaketen, **When** die Maintainerin die Graph-Ansicht aufruft, **Then** sieht sie Cluster-Knoten mit jeweiligem Risikoanteil als prozentualem Wert oder Balken.
2. **Given** ein dominanter Cluster, **When** die Cluster-Ansicht gerendert wird, **Then** ist der stärkste Risikokluster visuell eindeutig als führend erkennbar.
3. **Given** ein Cluster mit mehreren Dateien, **When** die Maintainerin auf den Cluster klickt, **Then** werden die enthaltenen Dateien und deren jeweiliger Einzelbeitrag aufgeklappt.

---

### User Story 4 - Entscheidung treffen und Ledger eintragen (Priority: P1)

Als Maintainerin treffe ich eine Merge-Entscheidung direkt im Cockpit: Ich bestätige die App-Empfehlung oder übersteige sie mit Begründung. Das Ergebnis wird im Decision Ledger mit Zeitstempel gespeichert.

**Why this priority**: Das Erfassen der menschlichen Entscheidung ist der eigentliche Governance-Akt — alles andere ist Vorbereitung.

**Independent Test**: Kann unabhängig getestet werden, indem ein Entscheidungsformular die Entscheidung speichert und ein Ledger-Eintrag mit Zeitstempel erscheint.

**Acceptance Scenarios**:

1. **Given** ein PR mit bekanntem Status, **When** die Maintainerin „Merge freigeben" oder „Ablehnen" im Formular auswählt und bestätigt, **Then** erscheint ein Ledger-Eintrag mit Zeitstempel, App-Empfehlung und menschlicher Entscheidung.
2. **Given** eine Entscheidung, die von der App-Empfehlung abweicht, **When** die Maintainerin die Bestätigung anklickt, **Then** ist das Begründungsfeld Pflicht; das Formular lässt sich ohne ausgefüllte Begründung nicht absenden.
3. **Given** ein bereits entschiedener PR, **When** eine zweite Sitzung denselben Ledger-Eintrag bearbeiten will, **Then** wird ein Versionskonflikt angezeigt und eine explizite Auflösung verlangt.

---

### User Story 5 - Decision Ledger und Outcomes nachverfolgen (Priority: P2)

Als Maintainerin öffne ich das Ledger für einen entschiedenen PR und sehe die chronologische Timeline aus Empfehlung, Entscheidung, Evidenz und — sobald verfügbar — 7- und 30-Tage-Outcomes.

**Why this priority**: Lernfähige Governance erfordert die Rückkopplung zwischen Entscheidungsqualität und realen Folgen.

**Independent Test**: Kann unabhängig getestet werden, indem ein Ledger-Eintrag Empfehlung, Entscheidung und Outcome-Felder (ausstehend oder befüllt) chronologisch zeigt.

**Acceptance Scenarios**:

1. **Given** ein entschiedener PR, **When** die Maintainerin das Ledger öffnet, **Then** zeigt die Timeline Empfehlung, finale Entscheidung und Evidenzreferenzen in chronologischer Reihenfolge.
2. **Given** ein PR ohne noch verfügbare Outcome-Daten, **When** der 7-Tage-Slot angezeigt wird, **Then** ist er explizit als ausstehend markiert, nicht leer gelassen.
3. **Given** ein PR mit eingegangenem 30-Tage-Outcome, **When** das Ledger neu geladen wird, **Then** ist der Outcome-Eintrag dem bestehenden Ledger-Eintrag zugeordnet, kein separater Datensatz.

---

### Edge Cases

- Was passiert, wenn für einen PR keine Cockpit-Analyse vorliegt (kein Scan durchgeführt)?
- Wie verhält sich die UI bei einer sehr großen Anzahl von Risikotreibern (>20)?
- Wie wird eine laufende Analyse (noch nicht abgeschlossen) dargestellt, ohne veraltete Daten zu zeigen? → Lade-Indikator mit schrittweisen Teilresultaten; kein Blockieren der Ansicht.
- Wie reagiert das Frontend auf ein Backend-Timeout oder nicht erreichbares API?
- Wie wird mit gleichzeitigen Sitzungen umgegangen, die denselben Ledger-Eintrag bearbeiten?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Das Frontend MUSS für jeden PR eine Decision-Panel-Seite bereitstellen, die Status, Konfidenzwert und Top-Risikotreiber in einem einzigen initialen Viewport darstellt.
- **FR-002**: Das Frontend MUSS den Status-Badge (Go, Go with Guardrails, No-Go) farblich und textuell eindeutig unterscheidbar anzeigen.
- **FR-003**: Das Frontend MUSS bei unzureichender Evidenz automatisch einen No-Go-Status mit erklärendem Hinweis rendern.
- **FR-004**: Das Frontend MUSS für jeden No-Go- oder Guardrails-PR eine Minimal-Safe-Plan-Liste mit Risiko-Delta, Score-Delta und Guardrail-Bedingungen anzeigen.
- **FR-005**: Das Frontend MUSS Guardrail-Bedingungen als abhakbare Checkliste darstellen, deren Erfüllungsstatus ohne Seiten-Reload aktualisiert wird.
- **FR-006**: Das Frontend MUSS eine Accountability-Graph-Ansicht bereitstellen, die PR-Änderungen in Risikocluster gruppiert und den prozentualen Risikoanteil pro Cluster visualisiert.
- **FR-007**: Das Frontend MUSS ein Entscheidungsformular bereitstellen, über das eine Maintainerin Go/No-Go/Guardrails-Entscheidungen treffen und abspeichern kann.
- **FR-008**: Das Frontend MUSS bei einer Entscheidung, die von der App-Empfehlung abweicht, ein Pflicht-Begründungsfeld einblenden und das Absenden ohne Begründung verhindern.
- **FR-009**: Das Frontend MUSS für jeden PR ein Decision Ledger anzeigen, das Empfehlung, menschliche Entscheidung, Evidenzreferenzen und Outcome-Felder (7/30 Tage) in einer Timeline darstellt.
- **FR-010**: Das Frontend MUSS fehlende Outcome-Daten explizit als ausstehend kennzeichnen, anstatt diese Felder leer zu lassen.
- **FR-011**: Das Frontend MUSS bei einem erkannten Versionskonflikt (gleichzeitige Bearbeitung) einen sichtbaren Konflikt-Banner anzeigen und eine Auflösung erzwingen.
- **FR-012**: Das Frontend MUSS bei Backend-Fehlern oder Timeouts eine nutzerfreundliche Fehlermeldung anzeigen, ohne in einen Leerzustand zu verfallen.
- **FR-013**: Das Frontend MUSS alle Cockpit-Funktionen aus einer zusammenhängenden Ansicht heraus zugänglich machen, ohne externe Werkzeuge zu benötigen.
- **FR-014**: Das Frontend MUSS responsiv sein und auf gängigen Desktop-Viewport-Breiten (≥1024px) vollständig nutzbar sein.
- **FR-015**: Jede PR-spezifische Ansicht (Decision Panel, Ledger, Graph) MUSS über eine stabile, direkt verlinkbare URL erreichbar sein (SSR-fähiges Routing).
- **FR-016**: Das Frontend MUSS eine GitHub PR-URL als Eingabe akzeptieren und daraus Repo-Owner, Repo-Name und PR-Nummer automatisch auflösen; fehlerhafte oder nicht auflösbare URLs MÜSSEN eine verständliche Fehlermeldung erzeugen.
- **FR-017**: Das Frontend MUSS einen laufenden Drift-Scan durch einen sichtbaren Lade-Indikator anzeigen und bereits verfügbare Teilresultate schrittweise einblenden; die Ansicht darf während eines laufenden Scans nicht blockiert werden.
- **FR-018**: Das Frontend MUSS die Backend-Basis-URL über eine Umgebungsvariable (`COCKPIT_API_URL`) konfigurierbar halten, sodass dasselbe Build sowohl lokal als auch remote betrieben werden kann.
- **FR-019**: Das Frontend MUSS als statische Assets vorgebaut werden können, die `drift cockpit serve` ohne externes Hosting-Setup ausliefert; ein separates Deployment-Werkzeug darf nicht vorausgesetzt werden.

### Key Entities *(include if feature involves data)*

- **Decision Panel**: Hauptansicht pro PR mit Status-Badge, Konfidenzwert und Risikotreiber-Liste.
- **Minimal Safe Plan Card**: Darstellung eines Plans mit Deltas und Guardrail-Checkliste.
- **Accountability Graph**: Interaktive Visualisierung von Risikoclustern und deren Anteil am Gesamtrisiko.
- **Decision Form**: Formular zur Erfassung der menschlichen Merge-Entscheidung inkl. Pflicht-Begründung bei Abweichung.
- **Ledger Timeline**: Chronologische Darstellung von Empfehlung, Entscheidung, Evidenz und Outcomes pro PR.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95 % aller Decision-Panel-Seiten laden vollständig (Status + Konfidenz + Risikotreiber) in unter 2 Sekunden bei einem Standard-Desktop-Browser.
- **SC-002**: 100 % der Entscheidungsformulare, die eine App-Abweichung enthalten, verhindern das Absenden ohne Begründung.
- **SC-003**: 100 % aller Ledger-Einträge zeigen Empfehlung, Entscheidung und Evidenzreferenz; fehlende Outcomes werden als ausstehend markiert.
- **SC-004**: Die Accountability-Graph-Ansicht rendert für PRs mit bis zu 50 Risikoclustern ohne Interaktionsverzögerung über 300 ms.
- **SC-005**: 90 % der Tester in einem Usability-Durchgang können eine Merge-Entscheidung ohne externe Dokumentation innerhalb von 3 Minuten abschließen.

## Assumptions

- Das Cockpit-Backend (specs/006-human-decision-cockpit) stellt eine stabile API bereit, die Decision Status, Minimal-Safe-Plans, Risk Clusters und Ledger-Einträge liefert.
- Das Frontend wird als statische Assets vorgebaut; `drift cockpit serve` liefert diese Assets aus, sodass kein externes Hosting-Setup benötigt wird.
- Das Frontend ist eine Next.js-Web-App mit Static Export (SSR at build time only); keine Browser-Extension, kein IDE-Plugin, keine reine SPA.
- Authentifizierung und Zugriffskontrolle sind in der ersten Version ausgeschlossen; der Fokus liegt auf dem Governance-Workflow.
- Nur Desktop-Viewports (≥1024px Breite) werden für v1 unterstützt; Mobile-Optimierung ist explizit zurückgestellt.
- Die Backend-API ist JSON-basiert, folgt den bestehenden Drift-Output-Schemata und wird über eine konfigurierbare URL (`COCKPIT_API_URL`) angesprochen.
- PRs werden über ihre vollständige GitHub-PR-URL identifiziert; das Cockpit leitet daraus Repo-Owner, Repo-Name und PR-Nummer ab.
