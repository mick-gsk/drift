# Data Model: VS Code Copilot Chat Workflow Integration

**Feature**: `002-vscode-copilot-workflow`

---

## Entities

### 1. `TopFinding`

Represents a single finding surfaced in the HandoffBlock and session file. Immutable.

```python
class TopFinding(BaseModel, frozen=True):
    signal_type: str                    # e.g. "pattern_fragmentation"
    severity: str                       # "critical" | "high" | "medium" | "low"
    file_path: str                      # repo-relative posix path
    line_range: tuple[int, int] | None  # (start, end) or None if file-level
    reason: str                         # human-readable finding message
    finding_id: str                     # opaque stable ID from the finding
```

**Derivation**: Built from `Finding` objects in `RepoAnalysis.findings`, sorted by severity descending. Top 5 selected (FR-002).

---

### 2. `SessionData`

Persisted to `.vscode/drift-session.json`. Represents the full analysis context for Copilot Chat.

```python
class SessionData(BaseModel, frozen=True):
    schema_version: str           # "1.0" — for future migration
    repo_path: str                # repo root as posix path
    analyzed_at: str              # ISO 8601 UTC timestamp
    drift_score: float            # rounded to 3 decimal places
    grade: str                    # e.g. "B"
    grade_label: str              # e.g. "Acceptable"
    top_findings: list[TopFinding]  # top 5 by severity (FR-002)
    findings_total: int           # total finding count
    critical_count: int
    high_count: int
```

**Storage**: `.vscode/drift-session.json` — always gitignored, never committed.  
**Format**: JSON (Pydantic `.model_dump_json(indent=2)`).

---

### 3. `HandoffBlock`

Rendered to terminal (Rich) and embedded in JSON output. Immutable.

```python
class HandoffBlock(BaseModel, frozen=True):
    drift_score: float
    grade: str
    analyzed_at: str              # ISO 8601
    top_findings: list[TopFinding]  # same top 5 as session
    prompts: list[str]            # ["drift-fix-plan", "drift-export-report", "drift-auto-fix-loop"]
    session_file: str             # ".vscode/drift-session.json"
    findings_total: int
```

**Rich rendering**: Rich `Panel` with a `Table` of top findings + a line of clickable prompt names.  
**JSON rendering**: `copilot_handoff` key added to `analysis_to_json()` output dict.

---

## Relationships

```
RepoAnalysis
    │
    ├──(top 5 findings by severity)──► TopFinding[]
    │                                       │
    │                                       ▼
    │                               SessionData ──► .vscode/drift-session.json
    │                                       │
    │                                       ▼
    └──────────────────────────────► HandoffBlock
                                        │
                                        ├──(Rich Panel)──► terminal
                                        └──(JSON dict)──► "copilot_handoff" key
```

---

## State Transitions

```
drift analyze runs
    │
    ▼
analysis: RepoAnalysis  ──► save_last_scan()
    │
    ▼
build_session_data(analysis) ──► SessionData (pure)
    │
    ├──► write_session_file(repo, session_data)  ──► .vscode/drift-session.json
    │
    ▼
build_handoff_block(session_data) ──► HandoffBlock (pure)
    │
    ├── [output_format == "rich"] ──► render_handoff_rich(block, console)
    └── [output_format == "json"] ──► handoff_to_dict(block) ──► "copilot_handoff" key
```

---

## Validation Rules

| Field | Rule |
|-------|------|
| `TopFinding.severity` | Must be one of `"critical"`, `"high"`, `"medium"`, `"low"` |
| `TopFinding.file_path` | Posix, repo-relative |
| `SessionData.schema_version` | Must be `"1.0"` |
| `SessionData.drift_score` | `0.0 <= x <= 1.0` |
| `HandoffBlock.prompts` | Must contain exactly 3 entries |
| `HandoffBlock.session_file` | Always `".vscode/drift-session.json"` |

---

## New Source Module Layout

```
src/drift/copilot_handoff/
├── __init__.py       # Exports: build_session_data, write_session_file,
│                     #          build_handoff_block, render_handoff_rich,
│                     #          handoff_to_dict
├── _models.py        # TopFinding, SessionData, HandoffBlock (frozen Pydantic)
├── _session.py       # build_session_data(analysis) -> SessionData
│                     # write_session_file(repo: Path, data: SessionData) -> Path | None
└── _handoff.py       # build_handoff_block(session: SessionData) -> HandoffBlock
                      # render_handoff_rich(block: HandoffBlock, console: Console) -> None
                      # handoff_to_dict(block: HandoffBlock) -> dict
```

---

## Test Coverage Requirements

```
tests/test_copilot_handoff.py
├── test_build_session_data_top5_by_severity()
├── test_build_session_data_fewer_than_5_findings()
├── test_build_session_data_empty_findings()
├── test_write_session_file_creates_file(tmp_path)
├── test_write_session_file_skips_when_no_vscode_dir(tmp_path)
├── test_write_session_file_is_valid_json(tmp_path)
├── test_build_handoff_block_has_3_prompts()
├── test_handoff_to_dict_schema()
├── test_render_handoff_rich_no_exception(capsys)
├── test_session_data_roundtrip_write_and_read(tmp_path)
└── test_analysis_to_json_includes_copilot_handoff_when_passed()
```
