# Scoring Model

## Composite Drift Score

Individual signal scores are combined into a weighted composite:

$$\text{Score} = \frac{\sum (\text{signal\_weight} \times \text{signal\_score})}{\sum \text{weights}}$$

## Count Dampening

Logarithmic dampening prevents signals with many low-confidence findings from dominating:

$$\text{signal\_score} = \overline{s} \times \min\!\left(1,\; \frac{\ln(1 + n)}{\ln(1 + k)}\right)$$

- $\overline{s}$ = mean finding score
- $n$ = finding count
- $k$ = dampening constant (default: 10)

**Effect:** 1 finding at 0.5 → dampened to 0.27. 15 findings at 0.5 → full 0.5.

## Default Weights (v0.7.1)

All 13 signals are scoring-active since v0.7.0. Weights are normalised at runtime; `auto_calibrate` (default: on) rebalances based on signal variance.

| Signal | Weight | Rationale |
|---|---|---|
| Pattern Fragmentation (PFS) | 0.16 | Highest ablation-study impact on F1 |
| Architecture Violation (AVS) | 0.16 | Critical for maintainability |
| Mutant Duplicate (MDS) | 0.13 | Common AI pattern |
| Temporal Volatility (TVS) | 0.13 | Predictive of future bugs |
| Explainability Deficit (EDS) | 0.09 | Important but noisy |
| System Misalignment (SMS) | 0.08 | Cross-module novelty detection |
| Doc-Implementation Drift (DIA) | 0.04 | Promoted from report-only (v0.7.0) |
| Broad Exception Monoculture (BEM) | 0.04 | Promoted from report-only (v0.7.0) |
| Test Polarity Deficit (TPD) | 0.04 | Promoted from report-only (v0.7.0) |
| Naming Contract Violation (NBV) | 0.04 | Added in v0.7.0 ([ADR-008](https://github.com/sauremilk/drift/blob/main/docs/adr/008-adr-008-signal-promotion.md)) |
| Guard Clause Deficit (GCD) | 0.03 | Promoted from report-only (v0.7.0) |
| Bypass Accumulation (BAT) | 0.03 | Added in v0.7.0 ([ADR-008](https://github.com/sauremilk/drift/blob/main/docs/adr/008-adr-008-signal-promotion.md)) |
| Exception Contract Drift (ECM) | 0.03 | Added in v0.7.1 ([ADR-008](https://github.com/sauremilk/drift/blob/main/docs/adr/008-adr-008-signal-promotion.md)) |

Core weights were originally calibrated via ablation study (remove each signal, measure F1 delta, assign proportional weight). Promoted signals received conservative initial weights. See [ADR-003](https://github.com/sauremilk/drift/blob/main/docs/adr/003-composite-scoring-model.md).

### Historical note

The v0.5 benchmark study used 6 core signals at higher weights (PFS=0.22, AVS=0.22, MDS=0.17, TVS=0.17, EDS=0.12, SMS=0.10) with 4 report-only signals at weight 0.00. Precision claims in the study apply to that model. See [ADR-007](https://github.com/sauremilk/drift/blob/main/docs/adr/007-consistency-proxy-signals.md) for the original report-only rationale.

## Severity Mapping

| Score Range | Severity |
|---|---|
| ≥ 0.70 | CRITICAL |
| 0.50–0.70 | HIGH |
| 0.30–0.50 | MEDIUM |
| < 0.30 | LOW |

## Module-Level Scoring

Findings are grouped by module path. Each module receives:

- Per-signal scores
- Composite score
- AI attribution ratio (% findings from AI-generated code)
- Top signal identifier
