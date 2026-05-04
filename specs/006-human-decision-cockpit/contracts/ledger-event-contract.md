# Ledger Event Contract

## Purpose

Definiert das append-only Eventmodell fuer Decision Ledger Timeline inkl. Human Override und Outcome-Nachtraegen.

## Event Types

1. `decision_recommended`
2. `decision_overridden`
3. `decision_confirmed`
4. `outcome_updated`
5. `version_conflict_raised`
6. `version_conflict_resolved`

## Common Envelope

Alle Events muessen folgende Felder enthalten:

- `event_id` (UUID)
- `event_type`
- `pr_id`
- `ledger_entry_id`
- `version`
- `actor`
- `occurred_at` (ISO-8601 UTC)
- `payload` (typabhaengig)

## Event Rules

### decision_recommended

Payload:
- `recommended_status`
- `confidence`
- `evidence_sufficient`
- `risk_driver_ids`

Validation:
- Wenn `evidence_sufficient=false`, dann `recommended_status=no_go`.

### decision_overridden

Payload:
- `recommended_status`
- `human_status`
- `override_reason`

Validation:
- `human_status != recommended_status`
- `override_reason` ist nicht leer.

### decision_confirmed

Payload:
- `status`
- `decision_actor`

Validation:
- Wird nur akzeptiert, wenn kein offener Versionskonflikt fuer den Eintrag existiert.

### outcome_updated

Payload:
- `window` (`7d|30d`)
- `state` (`pending|captured|not_available`)
- `rework_events` (optional)
- `merge_velocity_delta` (optional)

Validation:
- Bei `state=captured` muessen Messwerte vorhanden oder explizit `null` begruendet sein.

### version_conflict_raised

Payload:
- `expected_version`
- `actual_version`
- `attempted_action`

Validation:
- Event wird synchron zum API-Fehler `409` erzeugt.

### version_conflict_resolved

Payload:
- `resolution_strategy` (`reload_and_retry|manual_merge|abort`)
- `new_version`

## Ordering and Idempotency

- Reihenfolge pro `pr_id` ist durch `version` monoton steigend.
- Duplicate `event_id` muss verworfen werden.
- `outcome_updated` fuer dieselbe `window` ersetzt nur den Snapshotzustand, aber bleibt als Event historisch erhalten.

## Audit Guarantees

- Jeder Unterschied zwischen Empfehlung und Human-Entscheidung ist ueber `decision_overridden` nachvollziehbar.
- Fehlende Outcomes sind als `pending` bzw. `not_available` explizit sichtbar.
- Parallele Schreibversuche sind durch Konflikt-Events forensisch nachvollziehbar.
