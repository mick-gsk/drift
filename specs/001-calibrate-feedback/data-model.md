# Data Model: Feedback-Based Signal Weight Calibration

**Phase 1 output for** `specs/001-calibrate-feedback`
**Date**: 2026-04-27
**Source**: Reverse-engineered from `src/drift/calibration/`

---

## Entities

### FeedbackEvent

**Source**: `src/drift/calibration/feedback.py`
**Pattern**: Python `@dataclass` (mutable, as it is created from parsed JSONL)

```python
@dataclass
class FeedbackEvent:
    signal_type: str                          # e.g. "PFS", "AVS"
    file_path: str                            # repo-relative path
    verdict: Literal["tp", "fp", "fn"]        # evidence verdict
    source: Literal["user", "inline_suppress",
                    "inline_confirm",
                    "git_correlation",
                    "github_api"]
    start_line: int | None = None
    timestamp: str = ""                       # ISO-8601, auto-set on create
    finding_id: str = ""                      # SHA-256[:16] of signal+file[+line]
    rule_id: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
```

**Validation rules**:
- `finding_id` auto-computed from `signal_type + file_path [+ start_line]` if absent
- `timestamp` auto-set to UTC ISO-8601 if absent
- `verdict` must be one of `tp | fp | fn` (enforced via `Literal`)
- `source` must be one of the 5 known source types

**State transitions**: Append-only. Once written to JSONL, events are immutable.
Deduplication happens at read-time (load → dedupe → calibrate).

**Deduplication key**: `(signal_type, file_path)` — one winner per signal×file pair.
**Priority**: `user=0 > inline_confirm/suppress=1 > github_api=2 > git_correlation=3`
(lower = higher priority, wins in dedup).

---

### SignalEvidence

**Source**: `src/drift/calibration/profile_builder.py`
**Pattern**: Python `@dataclass`

```python
@dataclass
class SignalEvidence:
    signal_type: str
    tp: int = 0
    fp: int = 0
    fn: int = 0

    # Derived (computed properties, not stored):
    total_observations: int   # tp + fp
    precision: float          # tp / (tp + fp), defaults to 1.0 if no observations
    recall_indicator: float   # tp / (tp + fn), defaults to 1.0 if no FN
```

---

### CalibrationResult

**Source**: `src/drift/calibration/profile_builder.py`
**Pattern**: Python `@dataclass`

```python
@dataclass
class CalibrationResult:
    calibrated_weights: SignalWeights
    evidence: dict[str, SignalEvidence]       # keyed by signal_type
    confidence_per_signal: dict[str, float]   # 0.0–1.0 per signal
    total_events: int
    signals_with_data: int

    def weight_diff(self, default_weights: SignalWeights) -> dict[str, dict[str, float]]:
        # Returns {signal_name: {default, calibrated, delta, confidence}}
        # Only includes signals where |delta| > 0.0001
        ...
```

---

### ScanSnapshot

**Source**: `src/drift/calibration/history.py`
**Pattern**: Dataclass; stored as JSON in `.drift/history/`

Represents a point-in-time drift scan result used for retrospective git-outcome correlation.

```python
@dataclass
class ScanSnapshot:
    timestamp: str           # ISO-8601
    drift_score: float
    finding_count: int
    findings: list[FindingSnapshot]
```

---

### SignalWeights

**Source**: `src/drift/config.py`
**Pattern**: Pydantic `BaseModel` (existing, not frozen — mutable for config load)

Holds per-signal weight floats. Used as both input (defaults) and output (calibrated)
of `build_profile`. Key method: `as_dict() -> dict[str, float]`.

---

## Persistence / Storage

| Artifact | Path | Format | Write pattern |
|----------|------|--------|---------------|
| Feedback events | `.drift/feedback.jsonl` | JSONL, UTF-8 | Append (+ FIFO cap) |
| Calibration status | `.drift/calibration_status.json` | JSON | Atomic replace |
| Calibrated weights | `drift.yaml` → `weights:` | YAML | Atomic replace |
| Scan history | `.drift/history/*.json` | JSON | Append (one file per scan) |

**.gitignore contract**: `.drift/` MUST be listed in `.gitignore` (FR-001b).
`drift.yaml` is NOT ignored — it is version-controlled config.

---

## Calibration Formula

```
confidence(signal) = min(observation_count / min_samples, 1.0)

precision_scaled_weight = default_weight × observed_precision

# FN boost adjusts weight upward when FN recall indicator is poor:
fn_adjusted_precision = precision + fn_boost_factor × (1 - recall_indicator)

calibrated_weight = lerp(default_weight, fn_adjusted_precision × default_weight, confidence)
                  = default_weight + confidence × (fn_adjusted_precision - 1) × default_weight
```

**Boundary conditions**:
- 0 observations → confidence = 0.0 → calibrated = default
- `min_samples` observations → confidence = 1.0 → calibrated = precision-scaled
- observation count > `min_samples` → confidence stays capped at 1.0

---

## Gap Entities (new work needed)

### FeedbackCapConfig (new config field)

```yaml
# drift.yaml
calibration:
  max_feedback_events: 10000   # 0 = no cap (default)
```

Accessed via `cfg.calibration.max_feedback_events: int`.
**Implementation**: Add field to existing `CalibrationConfig` Pydantic model in `src/drift/config.py`.

### WritabilityCheck (not a new entity — a new guard in existing function)

`_write_calibrated_weights()` in `calibrate.py` gains a pre-check:
```python
if not os.access(config_path, os.W_OK):
    raise click.ClickException(
        f"Cannot write calibrated weights: '{config_path}' is not writable."
    )
```
No new entity needed.
