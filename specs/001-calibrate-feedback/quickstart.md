# Quickstart: Feedback-Based Signal Weight Calibration

**Feature**: `drift feedback mark` + `drift calibrate`

---

## Prerequisites

1. `drift.yaml` with calibration enabled:

   ```yaml
   calibration:
     enabled: true
   ```

2. `.gitignore` must include `.drift/` (auto-applied by `drift init`).

---

## Step 1 — Record Feedback

Mark a false positive from a drift finding:

```bash
drift feedback mark \
  --signal PFS \
  --file src/orders/order_service.py \
  --verdict fp
```

Mark a true positive:

```bash
drift feedback mark \
  --signal AVS \
  --file src/payments/checkout.py \
  --verdict tp
```

Mark a false negative (missed finding):

```bash
drift feedback mark \
  --signal EDS \
  --file src/legacy/old_module.py \
  --verdict fn
```

Events are stored in `.drift/feedback.jsonl` (local, not committed).

---

## Step 2 — Inspect Evidence

See what evidence has been collected per signal:

```bash
drift calibrate explain
```

Output:
```
Evidence Detail (17 events)

PFS
  TP=3  FP=9  FN=0  Precision=25.00%  Confidence=60.0%

AVS
  TP=4  FP=1  FN=0  Precision=80.00%  Confidence=25.0%
```

---

## Step 3 — Preview Calibration

Check what weights would change without writing:

```bash
drift calibrate run --dry-run
```

Output:
```
Calibration Result (17 events, 2 signals with data)

Signal                         Default  Calibrated     Delta  Conf.
-----------------------------------------------------------------
PFS                             0.1600      0.0400   -0.1200  60.0%
```

---

## Step 4 — Apply Calibration

Once you have ≥ 20 feedback events per signal for full confidence:

```bash
drift calibrate run
```

This writes the `weights:` section to your `drift.yaml`.

---

## Step 5 — Check Status

```bash
drift calibrate status
```

Output:
```
Feedback events: 20
Feedback path: /your/repo/.drift/feedback.jsonl
History snapshots: 3
Min samples for full confidence: 20
Auto-recalibrate: disabled
```

---

## Reset to Defaults

To remove calibrated weights and revert to defaults:

```bash
drift calibrate reset
```

---

## Tips

- Calibration with < 20 events per signal leaves that signal's weight at the default.
  Calibrate iteratively — mark findings for 2–4 weeks, then run.

- Use `--format json` for scripting:

  ```bash
  drift calibrate run --format json | jq '.weight_changes'
  ```

- To configure the feedback file size limit (default 10 000 events):

  ```yaml
  calibration:
    max_feedback_events: 5000   # FIFO — oldest events dropped first
  ```

- If `drift calibrate run` fails with "is not writable", check file permissions
  on `drift.yaml` (`ls -la drift.yaml`).
