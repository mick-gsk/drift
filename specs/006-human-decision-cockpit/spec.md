# Feature Specification: Drift Human Decision Cockpit

**Feature Branch**: `010-before-specify-hook`  
**Created**: 2026-05-01  
**Status**: Draft  
**Input**: User description: "Drift Human Decision Cockpit (Web App)"

## Clarifications

### Session 2026-05-01

- Q: Welcher Entscheidungsstatus gilt bei unzureichender Evidenz? → A: Automatisch No-Go, bis Evidenz nachgeliefert ist.
- Q: Wie sollen Konfidenz-Schwellen den Status bestimmen? → A: Feste Schwellen je Status (Go, Go with Guardrails, No-Go).
- Q: Darf die menschliche Entscheidung die App-Empfehlung übersteuern? → A: Ja, aber nur mit Pflicht-Begründung im Ledger.
- Q: Wie werden fehlende 7/30-Tage-Outcomes dargestellt? → A: Explizit als ausstehend markieren.
- Q: Wie werden gleichzeitige Änderungen am selben PR-Eintrag behandelt? → A: Versionskonflikt erzeugen und explizite Auflösung erzwingen.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Entscheidungsstatus in unter 2 Minuten (Priority: P1)

Als Maintainerin will ich pro Pull Request sofort einen klaren Entscheidungsstatus (Go, Go with Guardrails, No-Go) mit Konfidenz und Risikotreibern sehen, damit ich trotz hoher agentischer Änderungsrate eine belastbare Merge-Entscheidung treffen kann.

**Why this priority**: Ohne schnellen, belastbaren Entscheidungsstatus verfehlt das Produkt seinen Kernnutzen der menschlichen Governance.

**Independent Test**: Kann vollständig getestet werden, indem für einen PR ein Status, ein Konfidenzwert und Top-Risikotreiber angezeigt werden und eine Maintainerin auf Basis dieser Ansicht eine dokumentierte Entscheidung trifft.

**Acceptance Scenarios**:

1. **Given** ein analysierter PR mit ausreichender Evidenz, **When** die Maintainerin die PR-Seite öffnet, **Then** sieht sie genau einen Decision Status (Go, Go with Guardrails oder No-Go), einen Konfidenzwert und die Top-Risikotreiber.
2. **Given** ein PR mit mehreren Risikotreibern, **When** die Hauptansicht geladen wird, **Then** sind die Risikotreiber nach Einfluss auf den Entscheidungsstatus priorisiert dargestellt.

---

### User Story 2 - Minimal Safe Change Set bewerten (Priority: P1)

Als Maintainerin will ich für riskante PRs den kleinsten sicheren Gegenmaßnahmen-Plan sehen, damit ich gezielt nur die notwendigen Änderungen vor Merge verlangen kann.

**Why this priority**: Der Minimal-Safe-Plan reduziert unnötige Rework-Schleifen und macht No-Go/Guardrails-Entscheidungen operativ umsetzbar.

**Independent Test**: Kann unabhängig getestet werden, indem ein No-Go- oder Guardrails-Fall mindestens einen konkreten Minimal-Safe-Plan mit erwartetem Risiko-Delta und Score-Delta liefert.

**Acceptance Scenarios**:

1. **Given** ein PR mit Status No-Go, **When** die Maintainerin die Minimal-Safe-Karte öffnet, **Then** wird mindestens ein konkreter Plan mit erwarteter Risiko- und Score-Verbesserung angezeigt.
2. **Given** ein PR mit Status Go with Guardrails, **When** die Maintainerin einen Plan betrachtet, **Then** sieht sie die erwartete Veränderung relativ zur Zielschwelle vor Merge.

---

### User Story 3 - Accountability Graph für Risikocluster verstehen (Priority: P2)

Als Maintainerin will ich Änderungen nach Risikoauswirkung in Clustern visualisiert sehen, damit ich erkenne, welche Änderungsbereiche den Entscheidungsstatus treiben.

**Why this priority**: Die Cluster-Sicht erhöht Nachvollziehbarkeit und beschleunigt die Kommunikation konkreter Guardrails an Agenten oder Beitragende.

**Independent Test**: Kann unabhängig getestet werden, indem die Ansicht die PR-Änderungen in nachvollziehbare Cluster gruppiert und pro Cluster den Beitrag zum Risiko zeigt.

**Acceptance Scenarios**:

1. **Given** ein PR mit mehreren thematischen Änderungspaketen, **When** die Maintainerin den Accountability Graph öffnet, **Then** sieht sie Cluster mit jeweiligem Risiko-Beitrag.
2. **Given** ein dominanter Risikocluster, **When** die Cluster priorisiert dargestellt werden, **Then** ist der stärkste Treiber klar als solcher erkennbar.

---

### User Story 4 - Entscheidungen und Outcomes nachverfolgen (Priority: P2)

Als Maintainerin will ich Empfehlung, menschliche Entscheidung und reale Outcomes (7/30 Tage) in einer Timeline sehen, damit ich die Qualität vergangener Entscheidungen bewerten und kalibrieren kann.

**Why this priority**: Governance wird nur lernfähig, wenn Empfehlungen und echte Folgen über Zeit vergleichbar dokumentiert sind.

**Independent Test**: Kann unabhängig getestet werden, indem für mindestens einen PR ein Ledger-Eintrag mit Empfehlung, Entscheidung, Evidenz und Outcome-Zeitpunkten vorhanden ist.

**Acceptance Scenarios**:

1. **Given** ein entschiedener PR, **When** die Maintainerin das Decision Ledger öffnet, **Then** sieht sie Empfehlung, finale menschliche Entscheidung und verknüpfte Evidenz.
2. **Given** ein PR mit verfügbaren Nachlaufdaten, **When** 7- oder 30-Tage-Outcome vorliegt, **Then** wird der Outcome im selben Ledger-Eintrag nachvollziehbar ergänzt.

---

### Edge Cases

- Was passiert, wenn für einen PR keine ausreichende Evidenz für eine belastbare Empfehlung vorliegt?
- Wie wird verhindert, dass ein PR gleichzeitig mehrere Decision-Status erhält?
- Wie verhält sich das System, wenn 7/30-Tage-Outcome-Daten noch nicht verfügbar sind?
- Wie wird ein bereits getroffener Entscheid dokumentiert, wenn sich die Evidenzlage vor Merge ändert?
- Bei unzureichender Evidenz wird der Status zwingend als No-Go gesetzt und erst nach Evidenz-Nachlieferung neu bewertet.
- Grenzfälle an den Schwellenwerten müssen deterministisch genau einem Status zugeordnet werden.
- Eine Abweichung zwischen App-Empfehlung und menschlicher Entscheidung ist nur mit dokumentierter Begründung zulässig.
- Fehlende 7/30-Tage-Outcomes werden im Ledger explizit als ausstehend ausgewiesen.
- Gleichzeitige Bearbeitungen desselben Ledger- oder Decision-Eintrags führen zu einem expliziten Versionskonflikt statt stiller Überschreibung.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Das System MUSS jedem analysierten PR genau einen Decision Status zuweisen (Go, Go with Guardrails oder No-Go).
- **FR-002**: Das System MUSS zu jedem Decision Status einen Konfidenzwert und priorisierte Top-Risikotreiber ausweisen.
- **FR-003**: Das System MUSS für jeden PR mit Status No-Go mindestens einen konkreten Minimal-Safe-Plan bereitstellen.
- **FR-004**: Das System MUSS für jeden Minimal-Safe-Plan ein erwartetes Risiko-Delta und ein erwartetes Score-Delta vor Merge ausweisen.
- **FR-005**: Das System MUSS Änderungen eines PR in Risikocluster gruppieren und den Beitrag jedes Clusters zum Entscheidungsstatus sichtbar machen.
- **FR-006**: Das System MUSS pro PR einen Ledger-Eintrag mit App-Empfehlung, menschlicher Entscheidung und referenzierter Evidenz speichern und anzeigen.
- **FR-007**: Das System MUSS Outcomes für Entscheidungen nach 7 und 30 Tagen im Ledger demselben PR-Eintrag zuordnen und als Verlauf darstellen.
- **FR-008**: Das System MUSS Guardrails-Entscheidungen mit klaren, prüfbaren Bedingungen dokumentieren, die vor Merge erfüllt sein müssen.
- **FR-009**: Das System MUSS Änderungen an Decision Status oder Entscheidungshistorie versioniert nachvollziehbar machen.
- **FR-010**: Das System MUSS eine Entscheidungsansicht bereitstellen, die den vollständigen Kern-Use-Case ohne Wechsel in andere Werkzeuge unterstützt.
- **FR-011**: Das System MUSS bei unzureichender Evidenz automatisch den Status No-Go setzen und bis zur Evidenz-Nachlieferung beibehalten.
- **FR-012**: Das System MUSS feste, statusspezifische Konfidenz-Schwellen für Go, Go with Guardrails und No-Go anwenden und Grenzwerte deterministisch auf genau einen Status mappen.
- **FR-013**: Das System MUSS menschliche Übersteuerungen der App-Empfehlung erlauben, jedoch nur bei verpflichtender Begründung, die im Ledger mit Zeitstempel gespeichert wird.
- **FR-014**: Das System MUSS nicht verfügbare 7/30-Tage-Outcomes explizit als ausstehend kennzeichnen, bis echte Outcome-Daten eingegangen sind.
- **FR-015**: Das System MUSS bei gleichzeitigen Änderungen am selben Decision- oder Ledger-Eintrag einen Versionskonflikt ausweisen und eine explizite Konfliktauflösung verlangen.

### Key Entities *(include if feature involves data)*

- **Pull Request Decision Record**: Repräsentiert die zusammengefasste Entscheidungsbasis pro PR mit Status, Konfidenz, Risikotreibern und Zeitstempel.
- **Minimal Safe Plan**: Repräsentiert die kleinste Gegenmaßnahme mit erwarteten Deltas und Zielschwellenbezug.
- **Risk Cluster**: Repräsentiert eine Gruppe zusammenhängender Änderungen mit aggregierter Risikoauswirkung.
- **Ledger Entry**: Repräsentiert die Timeline aus Empfehlung, menschlicher Entscheidung, Evidenzreferenzen und 7/30-Tage-Outcomes.
- **Guardrail Condition**: Repräsentiert eine konkrete Vor-Merge-Bedingung, deren Erfüllung überprüfbar ist.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% der analysierten PRs zeigen innerhalb von 2 Minuten nach Öffnen der PR-Seite einen vollständigen Decision Panel Status mit Konfidenz und Top-Risikotreibern.
- **SC-002**: 100% aller No-Go-Entscheidungen enthalten mindestens einen konkreten Minimal-Safe-Plan mit erwarteten Risiko- und Score-Deltas.
- **SC-003**: 100% aller menschlichen Entscheidungen sind im Ledger mit Empfehlung und Evidenz nachvollziehbar dokumentiert.
- **SC-004**: Für mindestens 90% der entschiedenen PRs werden verfügbare 7/30-Tage-Outcomes im gleichen Ledger-Kontext erfasst, sobald diese vorliegen.
- **SC-005**: Im Vergleich zur Baseline sinkt die Rate von post-merge Rework-Ereignissen um mindestens 20%, ohne dass die mediane Merge-Durchlaufzeit steigt.

## Assumptions

- Die Web App richtet sich primär an Maintainer und Reviewer mit Merge-Verantwortung in AI-first Repositories.
- Eine PR kann zu jedem Zeitpunkt nur einen aktiven Entscheidungsstatus besitzen; Statuswechsel werden historisiert.
- Für die initiale Version steht eine konsistente Evidenzbasis pro PR bereit, aus der Risiko- und Score-Deltas abgeleitet werden können.
- Nicht verfügbare 7/30-Tage-Outcomes werden im Ledger als ausstehend markiert und später ergänzt.
- Der Fokus der ersten Version liegt auf Governance-Entscheidung für Pull Requests, nicht auf zeilenbasierter Code-Review-Ersetzung.