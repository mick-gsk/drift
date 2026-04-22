# Agent-Auftrag

## Ziel

> Architektonische Erosion in Python-Codebases erkennen und handlungsfähige Empfehlungen geben

Kategorie: **utility**

## Constraints (automatisch generiert)

Die folgenden Anforderungen MÜSSEN bei der Implementierung eingehalten werden.
Nach jedem Modul / jeder Funktion stoppen und auf Validierung warten.

- [🔴 CRITICAL] **persist-survive-restart** → Gate: `BLOCK`: Application state must be persisted to durable storage; in-memory-only state is insufficient.
  Signal: `exception_contract_drift`
- [🟡 HIGH] **persist-concurrent-safety** → Gate: `BLOCK`: Concurrent write access must use transactions or locking to prevent data races and lost updates.
  Signal: `exception_contract_drift`
- [🟡 HIGH] **persist-input-integrity** → Gate: `BLOCK`: Input validation must occur before persistence; malformed data must not corrupt stored state.
  Signal: `guard_clause_deficit`
- [🔴 CRITICAL] **sec-no-plaintext-secrets** → Gate: `BLOCK`: Passwords and sensitive credentials must be hashed or encrypted; plaintext storage is forbidden.
  Signal: `hardcoded_secret_candidate`
- [🟡 HIGH] **sec-input-validation** → Gate: `BLOCK`: All user inputs must be validated and sanitized before processing to prevent injection attacks.
  Signal: `guard_clause_deficit`
- [🟡 HIGH] **sec-external-data-validation** → Gate: `BLOCK`: Data from external sources must be validated for schema conformance and integrity before use.
  Signal: `guard_clause_deficit`
- [🟢 MEDIUM] **err-user-friendly-messages** → Gate: `REVIEW`: Exceptions must be caught and translated to user-facing messages; raw tracebacks must not leak.
  Signal: `broad_exception_monoculture`
- [🟡 HIGH] **err-empty-input-resilience** → Gate: `BLOCK`: Empty or null inputs must be handled gracefully without causing unhandled exceptions or crashes.
  Signal: `guard_clause_deficit`
- [🟡 HIGH] **err-network-data-safety** → Gate: `BLOCK`: Network failures must be caught; partial writes must be rolled back or retried to prevent silent data loss.
  Signal: `broad_exception_monoculture`
- [🟢 MEDIUM] **ext-python** → Gate: `REVIEW`: Support for Python functionality
  Signal: `guard_clause_deficit`
- [🟢 MEDIUM] **ext-architektonische** → Gate: `REVIEW`: Support for Architektonische functionality
  Signal: `guard_clause_deficit`
- [🟢 MEDIUM] **ext-codebases** → Gate: `REVIEW`: Support for Codebases functionality
  Signal: `guard_clause_deficit`
- [🟢 MEDIUM] **ext-erosion** → Gate: `REVIEW`: Support for Erosion functionality
  Signal: `guard_clause_deficit`
- [🟢 MEDIUM] **ext-empfehlungen** → Gate: `REVIEW`: Support for Empfehlungen functionality
  Signal: `guard_clause_deficit`

## Validierung

Nach jeder Änderung wird `drift intent run --phase 4` ausgeführt.
Der Commit ist erst erlaubt, wenn alle Contracts den Status `fulfilled` haben.

## Ablauf

1. Implementiere die nächste Funktion / das nächste Modul
2. Stoppe und warte auf `drift intent run --phase 4`
3. Behebe alle `violated`-Contracts
4. Wiederhole bis alle Contracts `fulfilled` sind

## Trigger

Der Agent-Regelkreis wird durch einen der folgenden Trigger aktiviert:

- **Datei-Edit**: Nach jeder Änderung an einer Quelldatei MUSS `drift_nudge(changed_files=[...])` aufgerufen werden (Post-Edit-Nudge-Vertrag, siehe `.github/copilot-instructions.md`).
- **Cron / Schedule**: Geplante Wiederholung über `.github/workflows/drift-baseline-persist.yml`.
- **PR-Event**: `action.yml` mit `comment: true` postet strukturierten Report am PR.

## Regelkreis

Der autonome Regelkreis durchläuft fünf Phasen. Jede Phase benennt das verbindliche Werkzeug.

1. **Analyze** — `drift analyze --format json` (oder MCP `drift_scan`) erzeugt strukturierte Findings gemäß `drift.output.schema.json`.
2. **Classify** — Jedes Finding wird über das Severity-Gate unten einem der drei Buckets `AUTO` / `REVIEW` / `BLOCK` zugeordnet.
3. **Decide** — Agent prüft zusätzlich `auto_repair_eligible` und `drift_nudge(...).safe_to_commit`. Bei `safe_to_commit=false` darf kein `AUTO` ausgeführt werden.
4. **Act** — `AUTO` → Patch anwenden. `REVIEW` → PR-Kommentar via `action.yml`. `BLOCK` → Workflow-Exit ≠ 0 und Issue-Filing.
5. **Feedback** — TP/FP über `drift feedback` markieren. Der Workflow `.github/workflows/drift-label-feedback.yml` speist Kalibrierung zurück.

## Severity-Gate

Verbindliches Routing (ADR-089, konservativ). Der Agent DARF dieses Mapping nicht umgehen.

| Severity | auto_repair_eligible | Gate | Aktion |
|---|---|---|---|
| low / info | true | `AUTO` | Patch direkt anwenden, wenn `safe_to_commit=true`. |
| low / info | false | `REVIEW` | Als PR-Kommentar eskalieren. |
| medium | egal | `REVIEW` | Als PR-Kommentar eskalieren. |
| high / critical | egal | `BLOCK` | CI-Exit ≠ 0 und Issue-Filing. |

Pro-Contract-Routing (aus `drift.intent.json`):

- **persist-survive-restart** (`critical`, auto_repair_eligible=`True`) → Gate: `BLOCK`
- **persist-concurrent-safety** (`high`, auto_repair_eligible=`True`) → Gate: `BLOCK`
- **persist-input-integrity** (`high`, auto_repair_eligible=`True`) → Gate: `BLOCK`
- **sec-no-plaintext-secrets** (`critical`, auto_repair_eligible=`True`) → Gate: `BLOCK`
- **sec-input-validation** (`high`, auto_repair_eligible=`True`) → Gate: `BLOCK`
- **sec-external-data-validation** (`high`, auto_repair_eligible=`True`) → Gate: `BLOCK`
- **err-user-friendly-messages** (`medium`, auto_repair_eligible=`True`) → Gate: `REVIEW`
- **err-empty-input-resilience** (`high`, auto_repair_eligible=`True`) → Gate: `BLOCK`
- **err-network-data-safety** (`high`, auto_repair_eligible=`True`) → Gate: `BLOCK`
- **ext-python** (`medium`, auto_repair_eligible=`False`) → Gate: `REVIEW`
- **ext-architektonische** (`medium`, auto_repair_eligible=`False`) → Gate: `REVIEW`
- **ext-codebases** (`medium`, auto_repair_eligible=`False`) → Gate: `REVIEW`
- **ext-erosion** (`medium`, auto_repair_eligible=`False`) → Gate: `REVIEW`
- **ext-empfehlungen** (`medium`, auto_repair_eligible=`False`) → Gate: `REVIEW`

## Approval-Gate

`BLOCK`- und `REVIEW`-Findings werden nur durch einen Menschen freigegeben.

- Der Agent MUSS einen Vorschlag in `work_artifacts/agent_run_<timestamp>.md` ablegen, bevor er wartet.
- CI akzeptiert das Gate nur, wenn entweder das Label `drift/approved` durch einen Maintainer gesetzt ist oder `drift_nudge(...).safe_to_commit=true`.
- Der Agent DARF dieses Gate nicht selbst setzen, überspringen oder umschreiben. Bypass-Versuche werden von `scripts/verify_gate_not_bypassed.py` erkannt.

## Feedback-Loop

- True-Positive / False-Positive: `drift feedback mark --finding <id> --outcome tp|fp`.
- Label-basierter Feedback-Pfad: PR-Labels werden durch `.github/workflows/drift-label-feedback.yml` in Kalibrierungsinput übersetzt.
- Der Agent schreibt einen `AgentAction(action_type=feedback, ...)`-Eintrag in `agent_telemetry.agent_actions_taken` (Schema 2.2, ADR-090).

## Rollback-Trigger

- Wenn `drift_nudge(...).revert_recommended == true`: Edit SOFORT revertieren und einen anderen Ansatz wählen.
- Wenn ein `AUTO`-Patch bei erneutem `drift_nudge` `direction: degrading` liefert: Patch revertieren und auf `REVIEW` eskalieren.
- Rollback wird in `agent_telemetry.agent_actions_taken` mit `action_type: revert` und `reason: reverted_on_degrading` dokumentiert (Schema 2.2, ADR-090).
