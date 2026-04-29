# CLI Contract: `drift calibrate` Command Group

**Feature**: Feedback-Based Signal Weight Calibration
**Interface type**: Click CLI subcommands
**Source**: `src/drift/commands/calibrate.py`

---

## Subcommands

### `drift calibrate run`

```
drift calibrate run [OPTIONS]

  Compute calibrated weights from all evidence sources.

Options:
  -r, --repo PATH     Repository root [default: .]
  --dry-run           Show changes without writing [default: false]
  -c, --config PATH   Path to drift.yaml [default: auto-discover]
  --format [text|json]  Output format [default: text]
```

**Exit codes**:
- `0` — Success (including "no data" case)
- `1` — Error (missing config, unwritable `drift.yaml`, unexpected failure)

**Text output (success with changes)**:
```
Calibration Result (N events, M signals with data)

Signal                         Default  Calibrated     Delta  Conf.
-----------------------------------------------------------------
AVS                             0.1600      0.1200   -0.0400  75.0%
```

**JSON output**:
```json
{
  "status": "calibrated",
  "total_events": 42,
  "signals_with_data": 3,
  "weight_changes": {
    "AVS": {
      "default": 0.16,
      "calibrated": 0.12,
      "delta": -0.04,
      "confidence": 0.75
    }
  },
  "dry_run": false
}
```

**JSON output (no data)**:
```json
{"status": "no_data", "message": "No feedback evidence found."}
```

---

### `drift calibrate explain`

```
drift calibrate explain [OPTIONS]

  Show detailed evidence per signal.

Options:
  -r, --repo PATH     Repository root [default: .]
  -c, --config PATH   Path to drift.yaml [default: auto-discover]
```

**Text output**:
```
Evidence Detail (N events)

AVS
  TP=12  FP=4  FN=1  Precision=75.00%  Confidence=80.0%
```

---

### `drift calibrate status`

```
drift calibrate status [OPTIONS]

  Show calibration profile status and freshness.

Options:
  -r, --repo PATH     Repository root [default: .]
  -c, --config PATH   Path to drift.yaml [default: auto-discover]
```

**Text output (enabled)**:
```
Feedback events: 42
Feedback path: /path/to/repo/.drift/feedback.jsonl
History snapshots: 5
Min samples for full confidence: 20
Auto-recalibrate: disabled
```

**Text output (disabled)**:
```
Calibration is not enabled. Set calibration.enabled: true in drift.yaml
```

---

### `drift calibrate reset`

```
drift calibrate reset [OPTIONS]

  Remove calibrated weights and revert to defaults.

Options:
  -r, --repo PATH     Repository root [default: .]
  -c, --config PATH   Path to drift.yaml [default: auto-discover]
```

**Text output (weights present)**:
```
Calibrated weights removed. Defaults will be used.
```

**Text output (no weights)**:
```
No custom weights found in config.
```

---

## Library Contract: `drift.calibration`

Public API (from `src/drift/calibration/__init__.py`):

```python
from drift.calibration import FeedbackEvent, build_profile, load_feedback, record_feedback

# Record a feedback event
record_feedback(
    feedback_path=Path(".drift/feedback.jsonl"),
    event=FeedbackEvent(
        signal_type="PFS",
        file_path="src/foo.py",
        verdict="fp",
        source="user",
    ),
    max_feedback_events=10_000,   # NEW: FR-011b cap (0 = no cap)
)

# Load and calibrate
events = load_feedback(Path(".drift/feedback.jsonl"))
result = build_profile(
    events,
    default_weights=SignalWeights(),
    min_samples=20,       # observable spec contract
    fn_boost_factor=0.1,
)

# Inspect result
diff = result.weight_diff(SignalWeights())
# → {"AVS": {"default": 0.16, "calibrated": 0.12, "delta": -0.04, "confidence": 0.75}}
```

**Invariants**:
- `record_feedback()` is the ONLY function with side effects (file write)
- `build_profile()`, `load_feedback()`, `dedupe_feedback_events()` are pure
- All Pydantic models in `CalibrationResult` are read-only after construction
- No network access anywhere in `drift.calibration`
