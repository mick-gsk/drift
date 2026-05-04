# Research: Evidence-Based Drift Verification

**Phase 0 Output** | Feature 005 | 2026-05-01

## R-001: Existierendes JSON-Output-Schema

**Decision**: Evidence Package nutzt dieselbe `schema_version`-Konvention wie `drift analyze --format json`. Es wird ein eigenes top-level Feld `schema` (`"evidence-package-v1"`) eingeführt, um das neue Format eindeutig von `RepoAnalysis`-Output zu unterscheiden.

**Rationale**: Die bestehende Ausgabe via `analysis_to_json()` hat `schema_version = OUTPUT_SCHEMA_VERSION` und zahlreiche `RepoAnalysis`-spezifische Felder (`modules`, `findings`, `suppressed`). Das Evidence Package hat eine andere Semantik (Diff-level, nicht Repo-level) und muss ein eigenes Schema erhalten. Konsistenz in Namenskonvention und Serialisierungsform (JSON, `json.dumps`, `sort_keys=True`) wird beibehalten.

**Alternatives considered**:
- SARIF: Zu spezifisch auf statische Analyse ausgerichtet; fehlen `spec_confidence_score` und `action_recommendation` als Konzepte.
- RepoAnalysis wiederverwenden: Würde das Modell mit Diff-spezifischen Feldern verschmutzen (Constitution VI verletzt).

**Key implementation fact**: `drift.output.json_output` und `scripts/generate_output_schema.py` sind die kanonischen Orte für Schema-Definitionen. Ein neues Schema-Generierungsskript `scripts/generate_evidence_schema.py` folgt demselben Muster.

---

## R-002: Spec Confidence Score — Determinismus-Constraint

**Decision**: Der Spec Confidence Score wird **nicht** LLM-basiert berechnet, sondern als deterministischer Coverage-Score über die maschinenlesbaren Acceptance Scenarios in `spec.md`. Jedes Szenario wird gegen die gefundenen Violations, Testresultate und Lint-Status geprüft; der Score ist `passed_checks / total_checks`.

**Rationale**: Die Constitution sagt explizit „No LLM dependency: All 24 signals are deterministic static analysis; no network calls during analysis." Dieses Prinzip gilt auch für neue Features. Ein LLM-basierter Reviewer-Agent (FR-007) ist ein separater, optionaler Layer — er läuft **nach** der deterministischen Phase und sein Ergebnis fließt als `independent_review`-Abschnitt separat ins Evidence Package ein, beeinflusst aber den Score nur als additiver Confidence-Delta, nicht als Überschreibung.

**Alternatives considered**:
- Vollständig LLM-basiert: Verletzt Constitution; macht Score nicht reproduzierbar (SC-001/SC-004 verletzt).
- Hybrid mit LLM als primärem Scorer: Zu hohes Risiko für False-Confidence; LLM-Outputs sind nicht bit-identisch wiederholbar.

**Key implementation fact**: Die Acceptance Scenarios müssen als maschinenlesbare Prädikat-Liste vorliegen. Für v1 bedeutet das: FR-Checks (harte Invarianten) = 100% Gewicht im Struktur-Teil; Test/Lint-Status = Coverage-Anteil im Verifikations-Teil.

---

## R-003: Architectural Invariant Check — Bestehende Signale wiederverwenden

**Decision**: Layer-Verletzungen, verbotene Abhängigkeiten und File-Placement-Fehler werden über bestehende Drift-Signale (AVS, PFS, EDS) erkannt, **nicht** neu implementiert. Der Architectural Check ist ein thin Wrapper, der eine reguläre `drift analyze`-Analyse auf dem Diff-Snapshot durchführt und die Resultate in das Evidence Package überführt.

**Rationale**: Die 24 Signale in `src/drift/signals/` leisten bereits das, was der Architectural Check braucht. Eine Neuentwicklung würde dieselbe Logik duplizieren (Constitution V: YAGNI) und Precision/Recall-Tests für die Neuentwicklung erfordern, die bei Wiederverwendung überflüssig sind.

**Alternatives considered**:
- Eigener AST-basierter Checker: Massive Duplikation; schlechtere Präzision als die kalibrierten Signale.
- Statische Regel-Engine ohne Signale: Unflexibel; kein Lernmechanismus für neue Muster.

**Key implementation fact**: Der Diff wird in ein temporäres Worktree-Snapshot-Verzeichnis angewendet, dann `drift analyze` darauf ausgeführt (als Python-API, nicht als Subprocess). Die `RepoAnalysis`-Findings werden in `ViolationFinding`-Objekte konvertiert.

---

## R-004: Independent Reviewer Agent — Integrationsvertrag

**Decision**: Der Independent Reviewer Agent ist eine optionale, konfigurierbare Komponente. Für v1 nutzt er `drift.api.nudge` (den internen MCP-Nudge-Mechanismus) als Schnittstelle, um einen zweiten Kontext-Snapshot zu erstellen. Der Agent-Aufruf ist **kein direkter LLM-Call** aus dem Feature-Code; stattdessen wird ein strukturierter Diff-Report an einen MCP-Tool-Endpoint übergeben, der den Review ausführt.

**Rationale**: Die Constitution verbietet keine LLM-basierten Features generell, nur LLM-Abhängigkeiten in den 24 deterministischen Signalen. Eine separate Review-Komponente ist architektonisch sauber, wenn sie hinter einer Schnittstelle isoliert ist (Constitution I: Library-First, VI: Vertical Slice).

**Alternatives considered**:
- Direkter LLM-SDK-Call: Erzeugt Netzwerkabhängigkeit in der Kernbibliothek; verletzt Performance-Budget-Constraint.
- Kein Reviewer-Agent in v1: Würde SC-006 (+15 pp Erkennungsrate) unerreichbar machen.

**Key implementation fact**: Der Reviewer-Agent-Aufruf wird über eine `ReviewerAgentProtocol`-Schnittstelle abstrahiert. In Tests wird ein `MockReviewerAgent` injiziert. Timeout-Fallback ist Teil des Protokoll-Vertrags (FR-007).

---

## R-005: Rule-Promotion — Persistenzmodell

**Decision**: Wiederkehrende Verletzungsmuster werden in einer lokalen SQLite-Datenbank (oder als JSONL-Logfile) pro Repository gespeichert. Ab 5 Treffern desselben `(violation_type, file_pattern)`-Schlüssels wird ein `RulePromotionProposal`-Objekt erzeugt und im Evidence Package unter `rule_promotions` ausgegeben. Die Regel selbst wird **nicht automatisch aktiviert** — sie muss manuell via `drift rules add` akzeptiert werden.

**Rationale**: Automatische Aktivierung ohne Maintainer-Review wäre zu riskant (Constitution V: keine spekulativen Features). JSONL ist einfacher als SQLite für ein erstes Feature-Slice und vermeidet eine neue optionale Abhängigkeit.

**Alternatives considered**:
- Keine Persistenz in v1 (nur In-Memory): Macht Rule-Promotion-Zähler nicht sitzungsübergreifend — SC-005 wäre mit einem einzelnen Analyselauf nicht erfüllbar.
- Redis/Datenbank: Überdimensioniert; verletzt Constitution V.

**Key implementation fact**: Persistenz-Datei liegt unter `.drift/pattern_history.jsonl` im analysierten Repository. Das Format ist eine JSON-Zeile pro Treffer: `{"type": "...", "pattern": "...", "file": "...", "ts": "..."}`.

---

## R-006: Terminologie und Namenskonventionen (Constitution VI)

**Decision**: Das Feature lebt unter `src/drift/verify/` als eigenständiger Vertical Slice. Die öffentliche API ist `drift.verify`. Der CLI-Subcommand heißt `drift verify --diff <path> [--spec <path>]`.

**Rationale**: `verify` ist semantisch präzise, nicht mit bestehenden Commands (`analyze`, `check`, `brief`) kollisionsfrei und folgt der Verb-Konvention der CLI (Constitution IV).

**Alternatives considered**:
- `drift evidence`: Zu nah an Artefakt-Namen, nicht intuitiv als Verb.
- `drift review`: Kollidiert mit dem Konzept des Independent-Review-Agents.
- Erweiterung von `drift analyze`: Würde den bestehenden Analyze-Slice mit Diff-spezifischer Logik verschmutzen.

**Key implementation fact**: `src/drift/verify/` enthält: `__init__.py`, `_models.py`, `_checker.py` (deterministischer Layer), `_reviewer.py` (Reviewer-Agent-Protokoll + Mock), `_promoter.py` (Rule-Promotion), `_output.py`, `_cmd.py`.
