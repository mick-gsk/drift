# drift vs. Other Python Analysis Tools

> Which tool covers which gap? This page collects the practical differences
> between drift and adjacent static analysis, quality, and architecture tools.

## Capability Matrix

Data from [STUDY.md §9](https://github.com/sauremilk/drift/blob/master/STUDY.md)
(15-repository benchmark, 2 642 classified findings).

| Capability | drift | SonarQube | pylint / mypy | jscpd / CPD | Sourcegraph Cody |
|---|:---:|:---:|:---:|:---:|:---:|
| **Pattern Fragmentation** (N variants per module) | **Yes** | No | No | No | No |
| **Near-Duplicate Detection** (AST structural) | **Yes** | Partial (text) | No | Yes (text) | No |
| **Architecture Violation** (layer + circular deps) | **Yes** | Partial | No | No | No |
| **Temporal Volatility** (churn anomalies) | **Yes** | No | No | No | No |
| **Explainability Deficit** (complex undocumented fns) | **Yes** | Partial | Partial | No | No |
| **System Misalignment** (novel imports) | **Yes** | No | No | No | No |
| **Composite Health Score** | **Yes** | Yes (different) | No | No | No |
| **Trend Tracking** (score over time) | **Yes** | Yes | No | No | No |
| **Zero Config** (no server needed) | **Yes** | No (server) | Partial | Yes | No (cloud) |
| **SARIF Output** (GitHub Code Scanning) | **Yes** | Yes | No | No | No |
| **Deterministic** (no LLM in pipeline) | **Yes** | Yes | Yes | Yes | No |

## Tool-by-Tool Comparison

### SonarQube

**Strengths:** 25+ languages, security vulnerability detection (SAST), enterprise governance,
broad ecosystem integration.

**Limitations relative to drift:** No pattern-fragmentation signal. No temporal
volatility or system misalignment detection. Requires server infrastructure.
Duplication detection is text-based, not AST-structural.

**When to use both:** SonarQube for security/enterprise governance + drift for
cross-file coherence and AI-erosion-specific signals.

### pylint / mypy

**Strengths:** Style enforcement, type-safety checking, per-file rule violations.

**Limitations relative to drift:** No cross-file architectural analysis. No
composite codebase health metric. No detection of pattern fragmentation or
architecture boundary violations.

**When to use both:** pylint/mypy for local correctness + drift for structural
coherence.

### jscpd / CPD (Copy-Paste Detector)

**Strengths:** Fast text-level duplicate detection across many languages.

**Limitations relative to drift:** Text-based matching misses duplicates with
reformatting or variable renaming. No architecture awareness, no composite
scoring, no temporal signals.

**When to use both:** jscpd for broad text-level clone detection + drift for
AST-structural near-duplicates and architectural context.

### PyTestArch / architecture conformance tools

**Strengths:** Executable layer rules in pytest, declarative architecture
constraints.

**Limitations relative to drift:** Tests only explicitly declared boundaries —
does not detect emergent drift patterns like fragmentation, misalignment, or
volatility.

**When to use both:** PyTestArch for hard layer rules + drift for emergent
coherence signals. See [Drift vs Architecture Conformance Tools](drift-vs-architecture-conformance.md).

## Benchmark Scores on Real Repositories

All scores produced with default configuration (`drift analyze --since 90 --format json`).

| Repository | Files | Functions | Drift Score | Severity | Findings | Analysis Time |
|---|---:|---:|---:|---|---:|---:|
| Django | 2 890 | 31 191 | 0.596 | MEDIUM | 969 | 35.9 s |
| FastAPI | 664 | 3 902 | 0.624 | HIGH | 360 | 13.1 s |
| Pydantic | 403 | 8 384 | 0.577 | MEDIUM | 283 | 57.9 s |
| Celery | 371 | 7 546 | 0.578 | MEDIUM | 282 | 30.5 s |
| Flask | 65 | 1 405 | 0.358 | LOW | 18 | 4.7 s |
| drift (self) | 66 | 436 | 0.514 | MEDIUM | 80 | 0.4 s |

Source: [benchmark_results/all_results.json](https://github.com/sauremilk/drift/blob/master/benchmark_results/all_results.json)

## Recommended Stack

```
Linter (style)        → Ruff, pylint
Type checker (types)  → mypy, pyright
Coherence (drift)     → drift analyze / drift check
Security (SAST)       → Semgrep, CodeQL, SonarQube
```

Drift fills the coherence gap that the other three categories do not cover.

## Further Reading

- [Drift vs Ruff](drift-vs-ruff.md)
- [Drift vs Semgrep and CodeQL](drift-vs-semgrep-codeql.md)
- [Drift vs Architecture Conformance Tools](drift-vs-architecture-conformance.md)
- [Full Benchmark Study](../study.md)
