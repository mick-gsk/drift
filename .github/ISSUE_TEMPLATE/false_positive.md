---
name: "False Positive / False Negative"
about: "Drift is flagging something incorrectly, or missing a real issue"
title: "[FP/FN] "
labels: ["signal-quality"]
assignees: []
---

## Signal affected

<!-- Which signal produced the false result? Check one. -->

- [ ] Pattern Fragmentation (PFS)
- [ ] Architecture Violation (AVS)
- [ ] Mutant Duplicates (MDS)
- [ ] Explainability Deficit (EDS)
- [ ] Temporal Volatility (TVS)
- [ ] System Misalignment (SMS)
- [ ] Doc-Implementation Drift (DIA)
- [ ] Broad Exception Monoculture (BEM)
- [ ] Test Polarity Deficit (TPD)
- [ ] Guard Clause Deficit (GCD)
- [ ] Naming Contract Violation (NBV)
- [ ] Bypass Accumulation (BAT)
- [ ] Exception Contract Drift (ECM)
- [ ] Cohesion Deficit (COD)
- [ ] Co-Change Coupling (CCC)
- [ ] Missing Authorization (MAZ)
- [ ] Insecure Default (ISD)
- [ ] Hardcoded Secret (HSC)

## False positive or false negative?

- [ ] False positive — drift flagged something that isn't a real issue
- [ ] False negative — drift missed something that is a real issue

## Code example

```python
# Paste the relevant code snippet here
```

## Why this is incorrect

Explain why drift's assessment is wrong in this case.

## drift.yaml config (if any)

```yaml

```
