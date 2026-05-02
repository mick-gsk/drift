# Data Model: Drift Cockpit Frontend

**Phase**: 1  
**Date**: 2026-05-02  
**Source**: [spec.md](spec.md) + [research.md](research.md) + [cockpit-api.yaml](contracts/cockpit-api.yaml)

---

## Entities

### PrRef
Identifies a GitHub Pull Request parsed from its URL.

| Field | Type | Description |
|-------|------|-------------|
| `owner` | string | GitHub org/user (e.g. `mick-gsk`) |
| `repo` | string | Repository name (e.g. `drift`) |
| `pr_number` | number | Pull Request number |
| `raw_url` | string | Original GitHub PR URL (input) |

**Derivation**: Parsed from user input via regex on initial cockpit page load.

---

### DecisionPanel
The primary view state for a single PR.

| Field | Type | Notes |
|-------|------|-------|
| `pr_id` | string | Opaque backend ID (owner/repo/number) |
| `status` | `"go" \| "go_with_guardrails" \| "no_go"` | Exactly one per PR |
| `confidence` | number (0–1) | Threshold-driven |
| `evidence_sufficient` | boolean | False → status forced to `no_go` |
| `top_risk_drivers` | RiskDriver[] | Sorted descending by `impact` |
| `version` | number | Optimistic lock version |
| `scan_status` | `"complete" \| "running" \| "not_started"` | Drives loading indicator |
| `scan_progress` | number (0–100) | Only meaningful when `scan_status = "running"` |

---

### RiskDriver
A single risk factor contributing to the decision status.

| Field | Type | Notes |
|-------|------|-------|
| `driver_id` | string | Stable identifier |
| `title` | string | Human-readable label |
| `impact` | number | Contribution to total risk (0–1) |
| `severity` | `"critical" \| "high" \| "medium" \| "low"` | Optional badge |
| `cluster_id` | string | Optional — links to AccountabilityCluster |

---

### MinimalSafePlan
One actionable plan reducing risk for a No-Go or Guardrails PR.

| Field | Type | Notes |
|-------|------|-------|
| `plan_id` | string | Stable identifier |
| `pr_id` | string | Parent PR |
| `title` | string | Short plan label |
| `risk_delta` | number | Expected risk reduction (negative = improvement) |
| `score_delta` | number | Expected score change |
| `guardrails` | GuardrailCondition[] | Ordered checklist |

---

### GuardrailCondition
A single pre-merge condition within a plan.

| Field | Type | Notes |
|-------|------|-------|
| `condition_id` | string | Stable identifier |
| `description` | string | Human-readable requirement |
| `fulfilled` | boolean | Client-side toggle state (persisted via API) |

**UI state**: Toggled locally; debounced PATCH sent to API. All fulfilled → plan marked complete.

---

### AccountabilityCluster
A group of related PR changes, with aggregated risk contribution.

| Field | Type | Notes |
|-------|------|-------|
| `cluster_id` | string | Stable identifier |
| `label` | string | Thematic cluster name |
| `risk_share` | number (0–1) | Fractional contribution to total risk |
| `files` | ClusterFile[] | Member files and their individual contributions |
| `dominant` | boolean | True for the highest-risk cluster |

---

### ClusterFile
| Field | Type | Notes |
|-------|------|-------|
| `path` | string | Relative file path in PR |
| `contribution` | number (0–1) | Share within cluster |

---

### LedgerEntry
Full decision audit record for a PR.

| Field | Type | Notes |
|-------|------|-------|
| `entry_id` | string | Stable identifier |
| `pr_id` | string | Parent PR |
| `app_recommendation` | `DecisionStatus` | Backend recommendation |
| `human_decision` | `DecisionStatus \| null` | Set when decision is recorded |
| `override_justification` | string \| null | Required when human ≠ app |
| `decided_at` | ISO8601 string \| null | Timestamp of human decision |
| `evidence_refs` | string[] | References to evidence artifacts |
| `outcome_7d` | OutcomeRecord \| null | Null until data arrives |
| `outcome_30d` | OutcomeRecord \| null | Null until data arrives |
| `version` | number | Optimistic lock version |

---

### OutcomeRecord
| Field | Type | Notes |
|-------|------|-------|
| `window` | `"7d" \| "30d"` | Measurement window |
| `status` | `"pending" \| "available"` | `"pending"` shown as explicit label |
| `value` | string \| null | Outcome description (available when status = "available") |
| `recorded_at` | ISO8601 string \| null | When the outcome was recorded |

---

## State Transitions

### DecisionPanel scan_status
```
not_started → running → complete
                ↑           |
            (polling)   (stops)
```

### LedgerEntry
```
[created by backend]
  → human_decision = null (pending)
  → human_decision = set (decided)
  → outcome_7d.status = "available"
  → outcome_30d.status = "available"
```

### Version Conflict (optimistic lock)
```
Client sends version=N → Server has version=N+1
  → 409 VersionConflict
  → UI shows conflict banner
  → User resolves explicitly (reload + re-review)
```

---

## Client-Side State Shape (React context)

```typescript
interface CockpitStore {
  prRef: PrRef | null;
  panel: DecisionPanel | null;
  safePlans: MinimalSafePlan[];
  clusters: AccountabilityCluster[];
  ledger: LedgerEntry | null;
  scanPolling: boolean;
  conflictDetected: boolean;
  error: string | null;
}
```

All mutations go through API calls; no optimistic UI updates except guardrail toggles (debounced).
