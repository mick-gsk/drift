# Feature Specification: Evidence-Based Drift Verification

**Feature Branch**: `005-evidence-based-verification`  
**Created**: 2026-05-01  
**Status**: Draft  

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Änderung erhält vollständiges Evidenzpaket (Priority: P1)

Ein Agent oder Entwickler übergibt ein Change-Set (Diff) an das Verification-Feature. Das Feature führt alle Prüfungen durch und liefert ein reproduzierbares Evidenzpaket: Drift Score, Spec Confidence Score, vollständige Prüfliste mit Status, Fundstellen und Remediation-Hinweisen sowie eine maschinenlesbare Aktionsempfehlung.

**Why this priority**: Ohne dieses Kernergebnis hat das Feature keinen Nutzen. Alle anderen Stories bauen auf dem Evidenzpaket auf.

**Independent Test**: Kann vollständig getestet werden, indem ein synthetischer Diff übergeben wird und das Evidenzpaket auf Vollständigkeit (alle Pflichtfelder, reproduzierbarer Score) geprüft wird — ohne Review-Agent oder Rule-Promotion zu benötigen.

**Acceptance Scenarios**:

1. **Given** ein Agent liefert einen Diff, der keine Architekturverstöße enthält, **When** das Verification-Feature ausgeführt wird, **Then** erscheint eine Aktionsempfehlung `automerge`, ein Drift Score ≤ Schwellwert, ein Spec Confidence Score ≥ Schwellwert und eine leere Violations-Liste.
2. **Given** ein Agent liefert einen Diff mit einer Layer-Verletzung (UI-Schicht enthält Business-Logik), **When** das Verification-Feature ausgeführt wird, **Then** erscheint eine Aktionsempfehlung `needs_fix`, ein erhöhter Drift Score und mindestens ein Violation-Eintrag mit Fundstelle und Remediation-Hinweis.
3. **Given** das Feature wird zweimal mit identischem Diff aufgerufen, **When** die Ergebnisse verglichen werden, **Then** sind Drift Score, Spec Confidence Score und Violations-Liste identisch (Reproduzierbarkeit).

---

### User Story 2 — Architekturverstöße werden mit präziser Reparaturanweisung gemeldet (Priority: P2)

Ein Architektur-Check erkennt eine Verletzung einer harten Invariante (falsche Layer-Zuordnung, verbotene Abhängigkeit, File-Placement-Fehler). Das Feature gibt nicht nur eine Warnung aus, sondern eine agentenverständliche Reparaturanweisung, die die betroffene Stelle benennt und die korrekte Zielstruktur beschreibt.

**Why this priority**: Ein Verstoß ohne Remediation erzeugt manuellen Review-Aufwand. Mit präzisen Hinweisen kann ein Agent die Korrektur eigenständig anwenden.

**Independent Test**: Kann mit einem Diff getestet werden, der gezielt eine bekannte Layer-Verletzung enthält. Das Ergebnis muss die korrekte Datei/Zeile, den Verstoßtyp und eine konkrete Handlungsanweisung enthalten.

**Acceptance Scenarios**:

1. **Given** ein Diff verschiebt Business-Logik in eine UI-Komponente, **When** der Architectural Check läuft, **Then** enthält der Violation-Eintrag: Verstoßtyp `layer_violation`, betroffene Datei und Zeile, sowie den Text „Business-Logik in Service-Layer verschieben; UI darf nur Runtime-/Service-Schnittstellen konsumieren."
2. **Given** ein Diff fügt eine verbotene Abhängigkeit ein (z. B. direkte DB-Abfrage in einem CLI-Command), **When** der Dependency-Check läuft, **Then** enthält der Eintrag die Import-Zeile, den Verstoßtyp `forbidden_dependency` und einen Hinweis auf das erlaubte Zugriffsmuster.
3. **Given** ein Diff verletzt keine Architekturregeln, **When** die Prüfung läuft, **Then** enthält das Evidence Package keine Violation-Einträge mit Remediation-Hinweisen.

---

### User Story 3 — Unabhängiger Reviewer-Agent prüft auf blinde Flecken (Priority: P3)

Nach der automatischen Prüfung läuft ein unabhängiger Reviewer-Agent in einem frischen Kontext über die Änderung. Dieser identifiziert Edge Cases, Widersprüche zur Spec und strukturelle Probleme, die der primäre Prüfprozess nicht gefunden hat.

**Why this priority**: Einzelne Kontexte haben systematische blinde Flecken. Ein zweiter, unabhängiger Kontext erhöht die Erkennungsrate für Spec-Abweichungen und subtile Fehler.

**Independent Test**: Kann getestet werden, indem ein Diff mit einer bekannten, subtilen Spec-Abweichung (korrekte Tests, aber falsche Semantik) übergeben wird. Der Reviewer-Agent muss diesen Fall identifizieren, der Automatik-Check aber nicht.

**Acceptance Scenarios**:

1. **Given** ein Diff besteht alle automatischen Checks, enthält aber eine semantische Abweichung von der Spec, **When** der Reviewer-Agent läuft, **Then** meldet er mindestens einen Befund mit Bezug auf das verletzte Akzeptanzkriterium.
2. **Given** der Reviewer-Agent ist für einen Diff konfiguriert, **When** er ausgeführt wird, **Then** gibt es einen eigenen Abschnitt im Evidence Package mit Label `independent_review` und einem separaten Confidence-Delta.
3. **Given** der Reviewer-Agent findet keine zusätzlichen Probleme, **When** sein Ergebnis zusammengeführt wird, **Then** bleibt die Aktionsempfehlung unverändert.

---

### User Story 4 — Wiederkehrende Verletzungsmuster werden zu dauerhaften Regeln (Priority: P4)

Das Feature erkennt, wenn dasselbe Verletzungsmuster wiederholt auftritt, und ermöglicht dessen Überführung in eine dauerhafte Architektur- oder Cleanup-Regel, sodass künftige Änderungen automatisch gegen diese Regel geprüft werden.

**Why this priority**: Ohne diesen Mechanismus entsteht dieselbe Drift immer wieder. Dauerhafte Regeln machen die Erkennung mit der Zeit präziser und verringern den Review-Aufwand.

**Independent Test**: Kann getestet werden, indem dasselbe Verletzungsmuster fünfmal in verschiedenen Diffs auftritt und geprüft wird, ob das System eine Rule-Promotion vorschlägt und ob die neue Regel bei einem sechsten Diff automatisch greift.

**Acceptance Scenarios**:

1. **Given** dasselbe Verletzungsmuster tritt in mindestens fünf Diffs auf, **When** das Feature die Häufigkeit bewertet, **Then** erzeugt es einen Rule-Promotion-Vorschlag im maschinenlesbaren Format.
2. **Given** ein Rule-Promotion-Vorschlag wurde akzeptiert, **When** ein neuer Diff mit demselben Muster geprüft wird, **Then** wird der Verstoß durch die neue dauerhafte Regel erkannt, nicht durch Heuristik.
3. **Given** ein Muster tritt weniger als fünfmal auf, **When** das Feature die Häufigkeit bewertet, **Then** wird kein Rule-Promotion-Vorschlag erzeugt.

---

### Edge Cases

- **Leerer oder Whitespace-only Diff**: Das Feature liefert sofort ein Kurzresultat ohne Fehler — `automerge`, Drift Score 0, Spec Confidence Score 1.0, leere Violations-Liste und ein Hinweis `no_changes_detected` im Evidence Package.
- **Widerspüchliche Architekturregeln**: Beide Violations werden ausgegeben; die Aktionsempfehlung wird automatisch auf `needs_review` gesetzt, mit dem Hinweis `rule_conflict` und den IDs beider beteiligten Regeln im Evidence Package.
- **Reviewer-Agent Timeout / Kontextsüberlauf**: Das Feature scheitert nicht; es liefert das Evidenzpaket mit Aktionsempfehlung `needs_review` und dem Hinweis `independent_review_unavailable` im `independent_review`-Abschnitt.
- **Drift Score 0 bei niedriger Confidence**: `automerge` erfordert drift_score ≤ Schwellwert UND spec_confidence_score ≥ Schwellwert — beide Bedingungen müssen erfüllt sein. Ein Drift Score von 0.0 allein genügt nicht, wenn die Spec Confidence unter dem Schwellwert liegt.
- **Diffs mit mehreren Layers gleichzeitig**: Alle Violations aus allen betroffenen Layers werden gemeldet. Die `ActionRecommendation` richtet sich nach dem höchsten Severity-Wert: bei mindestens einer `critical`- oder `high`-Violation → `needs_fix`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Das System MUSS harte Invarianten (Layer-Verletzungen, verbotene Abhängigkeiten, File-Placement-Regeln, Naming-Konventionen) vor allen anderen Prüfungen auswerten.
- **FR-002**: Das System MUSS einen reproduzierbaren Drift Score pro Änderung berechnen, der widerspiegelt, wie stark die Änderung von Architektur- und Strukturregeln abweicht.
- **FR-003**: Das System MUSS einen reproduzierbaren Spec Confidence Score berechnen, der angibt, wie wahrscheinlich die Änderung die ursprüngliche Spec bzw. Akzeptanzkriterien erfüllt.
- **FR-004**: Das System MUSS für jede gefundene Verletzung einen Eintrag mit Verstoßtyp, Fundstelle (Datei und Zeile) und konkreter Remediation-Anweisung ausgeben.
- **FR-005**: Das System MUSS eine maschinenlesbare Aktionsempfehlung ausgeben: `automerge`, `needs_fix`, `needs_review` oder `escalate_to_human`.
- **FR-006**: Das System MUSS funktionale Evidenz einbeziehen: Testresultate, Lint-Ergebnisse, Typecheck-Ergebnisse, sowie optional Screenshots, Logs und Metriken. `FunctionalEvidence` wird vom Aufrufer als optionale Eingabe übergeben; `drift verify` sammelt diese Daten nicht selbst (kein interner `pytest`/`ruff`-Aufruf).
- **FR-007**: Das System MUSS einen unabhängigen Reviewer-Agenten **synchron** in einem frischen Kontext über die Änderung laufen lassen; die Aktionsempfehlung wird erst nach Vorliegen seines Ergebnisses erstellt. Bei Timeout oder Fehler des Reviewer-Agenten MUSS das Feature mit einem definierten Fallback-Verhalten abschließen (Aktionsempfehlung `needs-review`, Hinweis `independent_review_unavailable` im Evidence Package) statt mit einem Fehler zu scheitern.
- **FR-008**: Das System MUSS wiederkehrende Verletzungsmuster erkennen und ab einem konfigurierbaren Schwellwert einen Rule-Promotion-Vorschlag im maschinenlesbaren Format erzeugen.
- **FR-009**: Das System MUSS ein vollständiges **Evidence Package** als JSON mit eigenem Schema ausgeben (konsistent mit dem bestehenden `drift analyze --format json`-Format), das alle Prüfergebnisse, Scores, Violations und die Aktionsempfehlung enthält.
- **FR-010**: Eine Änderung darf nur `automerge` erhalten, wenn sowohl Drift Score als auch Spec Confidence Score die definierten Schwellwerte erfüllen und keine offenen Violations vorliegen.

### Key Entities

- **Change Set**: Die zu prüfende Änderung als Diff oder Dateiliste, zusammen mit Metadaten (Autor, Zeitstempel, optionale Spec-Referenz).
- **Evidence Package**: Vollständige Sammlung aller Prüfergebnisse für ein Change Set, enthält Drift Score, Spec Confidence Score, Violation-Liste, Independent Review und Aktionsempfehlung.
- **Violation Finding**: Einzelne gefundene Verletzung mit Verstoßtyp, Fundstelle, Schweregrad und Remediation-Anweisung.
- **Action Recommendation**: Maschinenlesbares Urteil (`automerge` | `needs_fix` | `needs_review` | `escalate_to_human`) mit Begründung.
- **Persistent Rule**: Dauerhaft gespeicherte Architektur- oder Cleanup-Regel, die aus einem wiederkehrenden Verletzungsmuster extrahiert wurde.
- **Independent Review Result**: Befunde des Reviewer-Agenten aus einem frischen Kontext, mit eigenem Confidence-Delta und Fundstellen.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Jede Änderung erhält innerhalb von 3 Minuten ein vollständiges, reproduzierbares Evidenzpaket mit allen Pflichtfeldern.
- **SC-002**: Architekturverstöße werden in 95 % der Fälle mit der korrekten Fundstelle (Datei und Zeile) und einer konkreten Remediation-Anweisung gemeldet.
- **SC-003**: Die Falsch-Positiv-Rate für Architektur-Violations liegt unter 5 % bei den definierten Testfixtures.
- **SC-004**: Eine Änderung erhält nur dann `automerge`, wenn alle Struktur- und Verifikationsprüfungen bestehen (100 % Konsistenz zwischen Prüfergebnis und Aktionsempfehlung).
- **SC-005**: Wiederkehrende Verletzungsmuster, die mindestens fünfmal in Diffs aufgetreten sind, werden zu mindestens 90 % als Rule-Promotion-Vorschlag erkannt.
- **SC-006**: Der Independent Review erhöht die Erkennungsrate für Spec-Abweichungen gegenüber dem reinen Automatik-Check um mindestens 15 Prozentpunkte (gemessen an Benchmark-Fixtures mit bekannten Abweichungen).

## Assumptions

- Die Architektur- und Strukturregeln des Repos (Layer-Grenzen, Dependency-Richtungen, Naming-Konventionen) liegen in maschinenlesbarer Form vor oder können aus bestehenden Artefakten (Golden Principles, `.github/instructions/`, Drift-Signalen) extrahiert werden.
- Der Reviewer-Agent verwendet dasselbe Modell wie der primäre Prüfprozess, läuft aber in einem frischen Kontext ohne Zugriff auf den primären Check-Verlauf.
- Screenshot- und Metriken-Evidenz ist optional und nur verfügbar, wenn eine Laufzeitumgebung bereitgestellt wird; das Feature funktioniert auch ohne diese Eingaben.
- Die Schwellwerte für Drift Score, Spec Confidence Score und den Rule-Promotion-Auslöser sind konfigurierbar und haben sinnvolle Standardwerte.
- Mobile-Unterstützung und UI-Visualisierung des Evidence Package sind für v1 außerhalb des Scope.
- Das Feature arbeitet auf Change-Set-Ebene (pro Diff), nicht auf Commit-History-Ebene; historische Analyse ist ein separates Feature.

## Clarifications

### Session 2026-05-01

- Q: Welches Output-Format soll das Evidence Package verwenden? → A: JSON mit eigenem Schema, konsistent mit `drift analyze --format json`
- Q: Ist "Evidence Package" der kanonische Begriff (statt "Evidence Report")? → A: Ja — "Evidence Package" ist der einzige kanonische Begriff; "Evidence Report" ist veraltet
- Q: Was soll das Feature bei einem leeren oder Whitespace-only Diff tun? → A: Sofort Kurzresultat liefern — automerge, Drift Score 0, Confidence 1.0, leere Violations, Flag `no_changes_detected`
- Q: Reviewer-Agent synchron oder asynchron? → A: Synchron; Aktionsempfehlung erst nach Reviewer-Ergebnis; bei Timeout Fallback auf `needs-review` + `independent_review_unavailable`
- Q: Verhalten bei widersprüchlichen Architekturregeln? → A: Beide Violations ausgeben, Aktionsempfehlung `needs-review`, Hinweis `rule_conflict` mit IDs beider Regeln
