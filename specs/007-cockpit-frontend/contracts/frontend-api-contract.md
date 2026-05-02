# Frontend–Backend Interface Contract

**Version**: 0.1.0  
**Date**: 2026-05-02  
**Source**: [cockpit-api.yaml](../../006-human-decision-cockpit/contracts/cockpit-api.yaml)  
**For**: Drift Cockpit Frontend ([spec.md](../spec.md))

---

## Base URL

Configured via environment variable `COCKPIT_API_URL` (default: `http://localhost:8001`).  
All paths below are relative to `$COCKPIT_API_URL/api/cockpit`.

---

## Endpoints consumed by the frontend

### Decision Panel

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/prs/{pr_id}/decision` | Fetch current Decision Panel (status, confidence, risk drivers) |
| `POST` | `/prs/{pr_id}/decision` | Record human decision (requires version for optimistic lock) |

**`pr_id` format**: `{owner}/{repo}/{pr_number}` — derived from GitHub PR URL by the frontend.

**POST body**:
```json
{
  "human_decision": "go | go_with_guardrails | no_go",
  "override_justification": "string | null",
  "version": 3
}
```
**409 Conflict** → `VersionConflict` response → frontend shows conflict banner.

---

### Scan Status (polling)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/prs/{pr_id}/scan-status` | Check if scan is running, complete, or not started |

**Response**:
```json
{
  "status": "running | complete | not_started",
  "progress": 45
}
```
Frontend polls every 3 seconds while `status = "running"`.

---

### Minimal Safe Plans

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/prs/{pr_id}/safe-plan` | Fetch all Minimal Safe Plans for the PR |
| `PATCH` | `/prs/{pr_id}/safe-plan/{plan_id}/guardrails/{condition_id}` | Toggle guardrail fulfillment |

**PATCH body**:
```json
{ "fulfilled": true }
```

---

### Accountability Clusters

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/prs/{pr_id}/clusters` | Fetch all risk clusters with file breakdown |

---

### Decision Ledger

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/prs/{pr_id}/ledger` | Fetch full ledger entry (recommendation + decision + outcomes) |

---

## Error Contract

All API errors return:
```json
{
  "error": "string",
  "detail": "string | null"
}
```

| HTTP Status | Frontend action |
|-------------|-----------------|
| 404 | Show "PR not found or not yet analysed" empty state |
| 409 | Show version conflict banner, block further edits |
| 422 | Show field-level validation error in form |
| 5xx | Show generic error message (FR-012) |
| Network error | Show "Backend not reachable" error (FR-012) |

---

## TypeScript Client Contract

The frontend generates a typed API client from this contract. Key types mirror `data-model.md` exactly. No extra fields may be assumed; unknown fields must be ignored gracefully.

**Client file location**: `packages/cockpit-ui/src/api/client.ts`

---

## Constraint: COCKPIT_API_URL injection

At Next.js build time, `COCKPIT_API_URL` is embedded via `next.config.js` `env` or `publicRuntimeConfig`. For `drift cockpit serve` local mode, the Python server injects the value pointing to `localhost:{api_port}`.
