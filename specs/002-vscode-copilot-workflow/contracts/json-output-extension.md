# Contract: JSON Output Extension (`copilot_handoff`)

**Affected file**: `src/drift/output/json_output.py` → `analysis_to_json()`  
**Change type**: Additive — new optional top-level key  
**Breaking change**: NO (key absent when not requested; consumers ignore unknown keys)

---

## JSON Output Extension

When `drift analyze --format json` is run from VS Code, the output JSON contains a new top-level key `copilot_handoff`:

```json
{
  "schema_version": "...",
  "version": "...",
  "drift_score": 0.423,
  "...",
  "copilot_handoff": {
    "drift_score": 0.423,
    "grade": "B",
    "analyzed_at": "2026-04-27T08:30:00Z",
    "session_file": ".vscode/drift-session.json",
    "findings_total": 12,
    "prompts": [
      "drift-fix-plan",
      "drift-export-report",
      "drift-auto-fix-loop"
    ],
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
}
```

---

## API Change: `analysis_to_json()`

```python
def analysis_to_json(
    analysis: RepoAnalysis,
    indent: int = 2,
    compact: bool = False,
    response_detail: str = "detailed",
    drift_score_scope: str | None = None,
    language: str | None = None,
    group_by: str | None = None,
    copilot_handoff: dict | None = None,  # NEW — optional
) -> str:
```

If `copilot_handoff` is not `None`, it is appended to the output dict:
```python
if copilot_handoff is not None:
    data["copilot_handoff"] = copilot_handoff
```

## API Change: `render_or_emit_output()`

```python
def render_or_emit_output(
    analysis,
    ...,
    copilot_handoff: dict | None = None,  # NEW — keyword-only, optional
) -> None:
```

Passed through to `analysis_to_json()` only when `output_format == "json"`.

---

## Backward Compatibility

- Existing callers of `analysis_to_json()` without the new param → no change in output.
- Existing consumers parsing the JSON output → `copilot_handoff` key is absent; no change.
- `drift.output.schema.json` (if maintained) should be updated to mark `copilot_handoff` as optional.
