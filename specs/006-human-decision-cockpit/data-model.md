# Data Model: Human Decision Cockpit

**Phase 1 Output** | Feature 006 | 2026-05-01

## Entities

### PullRequestDecisionRecord

Repraesentiert den aktuellen Entscheidungszustand fuer genau einen PR.

Fields:
- `pr_id: str`
- `status: DecisionStatus` (`go|go_with_guardrails|no_go`)
- `confidence: float` (0.0..1.0)
- `evidence_sufficient: bool`
- `risk_score: float`
- `score_delta_estimate: float`
- `top_risk_drivers: list[RiskDriver]`
- `active_version: int`
- `updated_at: datetime`

Validation:
- Genau ein aktiver Status pro `pr_id`.
- Wenn `evidence_sufficient == false`, dann `status == no_go`.

### RiskDriver

Ein priorisierter Risikotreiber im Decision Panel.

Fields:
- `driver_id: str`
- `title: str`
- `impact: float`
- `severity: str`
- `source_refs: list[str]`

### MinimalSafePlan

Kleinster Maßnahmen-Satz, der unter Zielschwelle fuehrt.

Fields:
- `plan_id: str`
- `pr_id: str`
- `steps: list[GuardrailCondition]`
- `expected_risk_delta: float`
- `expected_score_delta: float`
- `target_threshold: float`
- `feasible: bool`

Validation:
- Fuer `status == no_go` mindestens ein Plan mit `feasible == true`.

### GuardrailCondition

Pruefbare Bedingung fuer Guardrails-/No-Go-Aufloesung.

Fields:
- `condition_id: str`
- `description: str`
- `verification_method: str`
- `must_pass_before_merge: bool`

### AccountabilityCluster

Gruppiert Aenderungen nach Risikoauswirkung.

Fields:
- `cluster_id: str`
- `pr_id: str`
- `label: str`
- `files: list[str]`
- `risk_contribution: float`
- `dominant_drivers: list[str]`

### LedgerEntry

Historischer, auditierbarer Entscheidungsdatensatz.

Fields:
- `ledger_entry_id: str`
- `pr_id: str`
- `recommended_status: DecisionStatus`
- `human_status: DecisionStatus`
- `override_reason: str | null`
- `decision_actor: str`
- `evidence_refs: list[str]`
- `outcome_7d: OutcomeSnapshot`
- `outcome_30d: OutcomeSnapshot`
- `version: int`
- `created_at: datetime`
- `updated_at: datetime`

Validation:
- Wenn `human_status != recommended_status`, dann `override_reason` nicht leer.
- `version` muss bei Update monoton steigen.

### OutcomeSnapshot

Outcome-Status fuer 7 oder 30 Tage.

Fields:
- `window: str` (`7d|30d`)
- `state: OutcomeState` (`pending|captured|not_available`)
- `rework_events: int | null`
- `merge_velocity_delta: float | null`
- `captured_at: datetime | null`

## Relationships

- Ein `PullRequestDecisionRecord` hat 0..n `MinimalSafePlan`.
- Ein `PullRequestDecisionRecord` hat 0..n `AccountabilityCluster`.
- Ein `PullRequestDecisionRecord` hat 1..n `LedgerEntry` (zeitlicher Verlauf).
- Ein `LedgerEntry` enthaelt genau zwei `OutcomeSnapshot` (7d und 30d).

## State Transitions

DecisionStatus:
- `no_go -> go_with_guardrails` wenn Mindest-Guardrails erfuellt und Evidenz ausreichend.
- `go_with_guardrails -> go` wenn Restrisiko unter Go-Schwelle.
- `go|go_with_guardrails -> no_go` bei Evidenzverlust oder neuem kritischen Treiber.

OutcomeState:
- `pending -> captured` wenn reale Outcome-Daten eingehen.
- `pending -> not_available` wenn Outcome-Fenster endet ohne belastbare Daten.

Conflict Handling:
- Update auf `LedgerEntry` mit alter `version` erzeugt `VersionConflict` und verlangt explizite Aufloesung.
