# Contract: Session File Schema

**File**: `.vscode/drift-session.json`  
**Version**: `1.0`  
**Producer**: `src/drift/copilot_handoff/_session.py`  
**Consumers**: `.github/prompts/drift-fix-plan.prompt.md`, `drift-export-report.prompt.md`, `drift-auto-fix-loop.prompt.md`

---

## Schema

```json
{
  "schema_version": "1.0",
  "repo_path": ".",
  "analyzed_at": "2026-04-27T08:30:00Z",
  "drift_score": 0.423,
  "grade": "B",
  "grade_label": "Acceptable",
  "findings_total": 12,
  "critical_count": 0,
  "high_count": 3,
  "top_findings": [
    {
      "signal_type": "pattern_fragmentation",
      "severity": "high",
      "file_path": "src/myapp/utils.py",
      "line_range": [42, 67],
      "reason": "3 duplicate implementations of retry logic detected",
      "finding_id": "pfs-abc123"
    }
  ]
}
```

---

## Field Constraints

| Field | Type | Constraint |
|-------|------|-----------|
| `schema_version` | string | Always `"1.0"` |
| `repo_path` | string | Posix path, relative or absolute |
| `analyzed_at` | string | ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`) |
| `drift_score` | number | `0.0` – `1.0`, 3 decimal places |
| `grade` | string | One of: `A`, `B`, `C`, `D`, `F` |
| `grade_label` | string | Human-readable grade label |
| `findings_total` | integer | `>= 0` |
| `critical_count` | integer | `>= 0` |
| `high_count` | integer | `>= 0` |
| `top_findings` | array | 0–5 items, sorted severity-descending |
| `top_findings[].signal_type` | string | Signal type identifier |
| `top_findings[].severity` | string | `"critical"` \| `"high"` \| `"medium"` \| `"low"` |
| `top_findings[].file_path` | string | Posix, repo-relative |
| `top_findings[].line_range` | `[int, int]` \| null | `[start, end]` 1-based, or null |
| `top_findings[].reason` | string | Human-readable finding message |
| `top_findings[].finding_id` | string | Opaque stable ID |

---

## Backward Compatibility

- Consumers MUST tolerate additional keys (forward compat).
- Consumers SHOULD check `schema_version` before reading; if unknown, warn and continue.
- The file is regenerated on every `drift analyze` run. Consumers treat it as a snapshot.

---

## Staleness

If `analyzed_at` is more than 24 hours before current time: warn but continue (FR-007). The staleness check is the consumer's responsibility (implemented in prompt files, not in Python).
