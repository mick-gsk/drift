# API and Outputs

Drift exposes machine-consumable surfaces for automation, CI artifacts, and custom orchestration.

This page keeps the current surface area narrow and explicit.

## Agent-native workflow surface

Drift now exposes a consistent agent-oriented surface across Python API, MCP,
and top-level CLI commands:

- `drift validate`
- `drift scan`
- `drift diff`
- `drift fix-plan`
- `drift explain`

These commands map directly to the Python API functions `validate()`, `scan()`,
`diff()`, `fix_plan()`, and `explain()` in `drift.api`.

The agent-native commands are intended to replace ad-hoc shell parsing workflows.
They emit stable JSON payloads that are small by default and explicitly
decision-oriented.

## Agent decision fields

`drift scan` and `drift diff` include machine-oriented decision fields so agents
do not need to re-implement gating heuristics outside drift.

### `scan` response additions

- `accept_change`: `true` when no blocking reasons are present
- `blocking_reasons`: list of machine-readable reasons such as
    `existing_high_or_critical_findings` or `drift_trend_degrading`
- `critical_count`: total critical findings in the analyzed scope
- `high_count`: total high findings in the analyzed scope

### `diff` response additions

- `accept_change`: `true` when the diff introduces no blocking regressions
- `blocking_reasons`: list of machine-readable reasons such as
    `new_high_or_critical_findings` or `drift_score_regressed`
- `score_regressed`: whether the diff score increased
- `new_high_or_critical`: count of new high/critical findings in the diff
- `target_path`: optional scoped subpath used for decision logic
- `out_of_scope_new_count`: count of diff findings outside the scoped target path

When `target_path` is set on `drift diff`, drift evaluates acceptance primarily
against findings inside that path and separately reports out-of-scope noise via
`out_of_scope_new_count` and the blocking reason `out_of_scope_diff_noise`.

## Telemetry correlation

When telemetry is enabled, drift emits one JSONL event per API/tool call.
Events are correlated with a stable `run_id`.

- Set `DRIFT_TELEMETRY_RUN_ID` to provide an external workflow id.
- If omitted, drift generates one stable run id for the current process.

This makes it possible to reconstruct multi-step agent workflows across
`validate`, `scan`, `diff`, `fix-plan`, and `explain` calls.

## Python API entry points

### `analyze_repo`

```python
from pathlib import Path
from drift.analyzer import analyze_repo
from drift.config import DriftConfig

result = analyze_repo(
    repo_path=Path("."),       # Repository root
    config=None,               # DriftConfig instance or None for auto-detection
    since_days=90,             # Git history lookback window
    target_path=None,          # Restrict analysis to a subdirectory
    on_progress=None,          # Callback: (message, current, total) -> None
    workers=8,                 # Thread pool size for parallel parsing
)
```

### `analyze_diff`

```python
from drift.analyzer import analyze_diff

result = analyze_diff(
    repo_path=Path("."),       # Repository root
    config=None,               # DriftConfig instance or None
    diff_ref="HEAD~1",         # Git ref to diff against
    workers=8,                 # Thread pool size
    on_progress=None,          # Progress callback
    since_days=90,             # Git history lookback
)
```

Both return a `RepoAnalysis` dataclass.

### `RepoAnalysis` fields

| Field | Type | Description |
|-------|------|-------------|
| `repo_path` | `Path` | Repository root |
| `analyzed_at` | `datetime` | Timestamp of analysis |
| `drift_score` | `float` | Composite drift score (0.0–1.0) |
| `severity` | `Severity` | Overall severity level |
| `findings` | `list[Finding]` | All detected findings |
| `module_scores` | `list[ModuleScore]` | Per-module drift scores |
| `total_files` | `int` | Number of analyzed files |
| `total_functions` | `int` | Number of analyzed functions |
| `ai_attributed_ratio` | `float` | Fraction of AI-attributed commits |
| `analysis_duration_seconds` | `float` | Wall-clock duration |
| `trend` | `TrendContext \| None` | Score trend over time |
| `suppressed_count` | `int` | Findings suppressed by inline markers |
| `context_tagged_count` | `int` | Findings with context tags |

### `Finding` fields

| Field | Type | Description |
|-------|------|-------------|
| `signal_type` | `SignalType` | Signal that produced this finding |
| `rule_id` | `str` | Stable rule identifier (defaults to `signal_type.value`) |
| `severity` | `Severity` | Finding severity |
| `score` | `float` | Signal confidence score (0.0–1.0) |
| `impact` | `float` | Weighted impact after scoring |
| `title` | `str` | One-line summary |
| `description` | `str` | Detailed explanation |
| `fix` | `str \| None` | Suggested remediation |
| `file_path` | `Path \| None` | Primary affected file |
| `start_line` | `int \| None` | Start line |
| `end_line` | `int \| None` | End line |
| `related_files` | `list[Path]` | Additional affected files |
| `ai_attributed` | `bool` | Whether the code is AI-generated |
| `metadata` | `dict` | Signal-specific metadata |

### `DriftConfig` as a Pydantic model

Configuration can be constructed programmatically:

```python
from drift.config import DriftConfig, SignalWeights

config = DriftConfig(
    include=["**/*.py"],
    exclude=["**/test/**"],
    weights=SignalWeights(pattern_fragmentation=0.20),
    fail_on="high",
    auto_calibrate=True,
)
```

Or loaded from a YAML file:

```python
config = DriftConfig.load(Path("."))  # Auto-discovers drift.yaml
```

### Example: programmatic usage

```python
from pathlib import Path
from drift.analyzer import analyze_repo
from drift.config import DriftConfig

config = DriftConfig.load(Path("."))
result = analyze_repo(Path("."), config=config)

print(f"Drift score: {result.drift_score:.3f}")
print(f"Severity: {result.severity}")
print(f"Findings: {len(result.findings)}")

for f in sorted(result.findings, key=lambda x: x.impact, reverse=True)[:5]:
    print(f"  [{f.rule_id}] {f.title} (impact={f.impact:.3f})")
```

## When to prefer the Python API

Use the Python API when:

- you need direct access to structured analysis objects
- you want custom orchestration without shell parsing
- you want to embed drift inside a larger Python-based pipeline

Use the CLI when you only need stable commands in local or CI workflows.

## JSON output

`drift analyze --format json` serializes repository-level results into a structured payload that includes:

- version and repository path
- analyzed timestamp
- drift score and severity
- trend information when available
- summary counters
- module scores
- findings
- findings_compact (deduplicated compact view)
- compact_summary (decision-first counters for agent/CI usage)
- fix_first list (prioritized "fix first" items)
- remediation object per finding (when available)
- suppressed and context-tagged counts

This is the best current format for CI artifacts, snapshot comparison, and downstream scripts.

For token-efficient automation, use compact JSON mode:

```bash
drift analyze --format json --compact
drift check --format json --compact
```

Compact mode keeps top-level decision data (`drift_score`, `severity`, `fix_first`,
`findings_compact`, `compact_summary`) and omits heavy sections (`modules`, full `findings`).

## Exit code contract

Drift CLI process exit codes are stable and intended for CI routing:

| Exit code | Meaning | Typical action |
|---|---|---|
| `0` | Success (no blocking findings) | Continue pipeline |
| `1` | Severity gate failed (`--fail-on`) | Mark quality gate failed |
| `2` | Configuration or user input error | Fail fast, request config fix |
| `3` | Analysis pipeline error | Fail analysis stage, inspect error payload |
| `4` | System error (I/O, git, permissions) | Retry or fix environment |
| `130` | Interrupted (Ctrl+C) | Treat as cancelled run |

## Machine-readable CLI errors

For deterministic CI parsing, enable structured error payloads with:

```bash
DRIFT_ERROR_FORMAT=json drift analyze --repo . --format json
```

When enabled, drift emits one JSON object on `stderr` for runtime errors.

Current payload shape (`schema_version: "2.0"`):

```json
{
    "schema_version": "2.0",
    "type": "error",
    "error_code": "DRIFT-1001",
    "category": "user",
    "message": "[DRIFT-1001] bad config",
    "detail": "[DRIFT-1001] bad config\n\nRun 'drift explain DRIFT-1001' for details.",
    "exit_code": 2,
    "hint": "Run 'drift explain DRIFT-1001' for details.",
    "recoverable": true,
    "suggested_action": "Fix the value at line {line} or run 'drift config show' to see defaults"
}
```

Notes:

- Machine-readable error payloads are emitted on `stderr`.
- For machine output formats with `--output`, the actual analysis JSON/SARIF is written only to the target file.
- Human-readable error text remains the default when `DRIFT_ERROR_FORMAT` is not set to `json`.

## SARIF output

`drift analyze --format sarif` exports findings in SARIF 2.1.0 format.

Use SARIF when you want findings to flow into code scanning or tooling that already understands SARIF as a review surface.

Drift includes:

- rule IDs per signal
- severity mapping to SARIF levels
- primary locations and related locations
- optional fix text in result messages
- context properties for tagged findings
- trend properties when available

## Current practical boundary

Drift does not currently document a public HTTP API or OpenAPI surface.

That is intentional. The current machine-consumable contract is the CLI, JSON output, SARIF output, and the Python analysis entry points.

## Best uses today

- save JSON outputs as CI artifacts for historical comparison
- upload SARIF to GitHub code scanning
- call the Python API from internal tooling when you need direct object access

## Related pages

- [Integrations](../integrations.md)
- [CI Architecture Checks with SARIF](../use-cases/ci-architecture-checks-sarif.md)
- [Trust and Evidence](../trust-evidence.md)