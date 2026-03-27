# Signal Reference

Drift measures 13 scoring signals, each targeting a different dimension of architectural erosion. All signals contribute to the composite score (auto-calibrated at runtime). Signals are grouped by origin: 6 core signals (ablation-validated since v0.5), 4 consistency proxy signals (promoted from report-only in v0.7.0 via [ADR-007](https://github.com/sauremilk/drift/blob/main/docs/adr/007-consistency-proxy-signals.md)), and 3 contract signals (added in v0.7.0/v0.7.1 via [ADR-008](https://github.com/sauremilk/drift/blob/main/docs/adr/008-adr-008-signal-promotion.md)).

## Core Signals

### Pattern Fragmentation (PFS)

**What it detects:** Same category of pattern implemented N different ways within one module.

**Example:** Error handling split across try/except, bare except, logging-only, and re-raise patterns in the same API module.

**Score:** `1 - (1 / num_variants)` — 4 variants → 0.75 (HIGH)

### Architecture Violations (AVS)

**What it detects:** Imports that cross layer boundaries or create circular dependencies.

**Example:** A database model importing from an API route handler.

**Techniques:** Import graph analysis, layer inference, hub dampening, Tarjan SCC.

### Mutant Duplicates (MDS)

**What it detects:** Near-identical functions that diverge in subtle ways.

**Example:** `validate_user()` and `validate_admin()` sharing 90% identical AST structure.

**Techniques:** AST n-gram Jaccard similarity, LOC bucketing, optional FAISS embeddings.

### Explainability Deficit (EDS)

**What it detects:** Complex functions lacking docstrings, tests, or type annotations.

**Focus:** Especially flags AI-attributed functions (from git blame heuristics).

### Temporal Volatility (TVS)

**What it detects:** Files with anomalous change frequency, author diversity, or defect correlation.

**Techniques:** Statistical z-score on commit frequency, author entropy.

### System Misalignment (SMS)

**What it detects:** Recently introduced imports or patterns foreign to their target module.

**Example:** A utility module suddenly importing from an HTTP client library.

## Consistency Proxy Signals

Promoted from report-only to scoring-active in v0.7.0 with conservative initial weights. See [ADR-007](https://github.com/sauremilk/drift/blob/main/docs/adr/007-consistency-proxy-signals.md) for the original rationale.

### Doc-Implementation Drift (DIA)

**What it detects:** Documented architecture that no longer matches actual code.

**Weight:** 0.04. Known precision limitations from URL/directory-name heuristics (63% strict precision in v0.5 baseline).

### Broad Exception Monoculture (BEM)

**What it detects:** Modules where exception handling is uniformly broad (bare except, catch-all Exception) with high swallowing ratios.

**Weight:** 0.04.

### Test Polarity Deficit (TPD)

**What it detects:** Test suites with near-zero negative assertions — only happy-path testing, no failure-path coverage.

**Weight:** 0.04.

### Guard Clause Deficit (GCD)

**What it detects:** Modules where public functions uniformly lack early guard clauses (parameter validation, precondition checks).

**Weight:** 0.03.

## Contract Signals

Added in v0.7.0/v0.7.1 via [ADR-008](https://github.com/sauremilk/drift/blob/main/docs/adr/008-adr-008-signal-promotion.md).

### Naming Contract Violation (NBV)

**What it detects:** Modules where naming conventions diverge from the established codebase patterns (e.g., inconsistent casing, prefix/suffix drift).

**Weight:** 0.04.

### Bypass Accumulation (BAT)

**What it detects:** Modules accumulating bypass patterns (TODO/FIXME/HACK markers, disabled checks, hardcoded overrides) beyond a statistical threshold.

**Weight:** 0.03.

### Exception Contract Drift (ECM)

**What it detects:** Modules where exception hierarchies or error-handling contracts diverge from the dominant codebase pattern.

**Weight:** 0.03.
