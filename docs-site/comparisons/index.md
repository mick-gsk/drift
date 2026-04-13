# drift vs. Other Python Analysis Tools

> Which tool covers which gap? This page collects the practical differences
> between drift and adjacent static analysis, quality, and architecture tools.

## Capability Matrix

Data from [STUDY.md §9](https://github.com/mick-gsk/drift/blob/main/docs/STUDY.md)
(15-repository benchmark, 2 642 classified findings).

| Capability | drift | SonarQube | pylint / mypy | jscpd / CPD | DeepSource | GitHub Adv. Security |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Pattern Fragmentation** (N variants per module) | **Yes** | No | No | No | No | No |
| **Near-Duplicate Detection** (AST structural) | **Yes** | Partial (text) | No | Yes (text) | No | No |
| **Architecture Violation** (layer + circular deps) | **Yes** | Partial | No | No | No | No |
| **Temporal Volatility** (churn anomalies) | **Yes** | No | No | No | No | No |
| **Explainability Deficit** (complex undocumented fns) | **Yes** | Partial | Partial | No | Partial (AI) | No |
| **System Misalignment** (novel imports) | **Yes** | No | No | No | No | No |
| **Composite Health Score** | **Yes** | Yes (different) | No | No | Yes (different) | No |
| **Trend Tracking** (score over time) | **Yes** | Yes | No | No | Partial | No |
| **Zero Config** (no server needed) | **Yes** | No (server) | Partial | Yes | No (cloud) | No (GitHub-hosted) |
| **SARIF Output** (GitHub Code Scanning) | **Yes** | Yes | No | No | Yes | Yes |
| **Deterministic** (no LLM in pipeline) | **Yes** | Yes | Yes | Yes | **No** | Yes |
| **Security / SAST** | No | Yes | No | No | Partial | **Yes** |
| **Bayesian per-repo calibration** | **Yes** | No | No | No | No | No |
| **AI-specific coherence signals** | **Yes** | No | No | No | No | No |

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

### DeepSource

**Strengths:** Automated code review with AI-assisted autofix, GitHub/GitLab
integration, free tier for open-source, broad language support.

**Limitations relative to drift:** Analysis is LLM-based — results are
stochastic, not reproducible. The same code produces different results on
different runs, which makes it unsuitable for CI gates or compliance audits
that require deterministic, auditable output. No temporal signals, no
architecture-erosion-specific detection, no Bayesian per-repo calibration.

**When to use both:** DeepSource for general automated code review + drift
for deterministic architecture-erosion tracking in regulated or
compliance-sensitive contexts (FinTech, HealthTech, audit trails).

### GitHub Advanced Security / CodeQL

**Strengths:** Security vulnerability detection (SAST), secret scanning,
dependency review, native GitHub integration, Copilot Autofix for findings.
No separate tooling required for GitHub-native teams.

**Limitations relative to drift:** CodeQL finds security patterns — data
flows, injection paths, authorization gaps. It does not detect architecture
erosion: no mutant duplicate (MDS), no pattern fragmentation (PFS), no
architectural violation (AVS), no system misalignment (SMS), no temporal
volatility (TVS). These structural signals are outside CodeQL's design scope
by design.

**When to use both:** GitHub Advanced Security for security/compliance + drift
for the structural coherence layer that CodeQL does not cover. Drift's SARIF
output integrates natively with GitHub Code Scanning — both findings appear
in the same interface.

### GitHub Copilot Code Review (Agentic)

**Strengths:** Post-PR review with repository-wide context, CodeQL integration,
available to all paid Copilot subscribers without additional installation.

**Limitations relative to drift:** Copilot Code Review operates **after** the
code is written — it reviews PRs. Drift operates **before** (`drift brief`
generates guardrails before an agent task starts) and **during** (`drift nudge`
gives directional feedback inside the editing session). These are structurally
different positions in the developer workflow, not competing features.
Additionally: no deterministic score, no trend tracking, no temporal signals,
no per-repo Bayesian calibration.

**When to use both:** Use drift before the PR for pre-task guardrails and
inner-loop coherence feedback. Use Copilot Code Review on the PR for
post-task verification. See [Drift vs GitHub Copilot Code Review](drift-vs-copilot-review.md).

## Benchmark Scores on Real Repositories

!!! info "Benchmark context"
    All scores produced with default configuration (`drift analyze --since 90 --format json`), `src/`-scope shallow clone, Drift v2.5.x, April 2026. [Case Studies](../case-studies/index.md) use full-clone analysis with different file counts and scores.

| Repository | Files | Functions | Drift Score | Severity | Findings | Analysis Time |
|---|---:|---:|---:|---|---:|---:|
| Django | 2 890 | 31 191 | 0.596 | MEDIUM | 969 | 35.9 s |
| FastAPI | 664 | 3 902 | 0.624 | HIGH | 360 | 13.1 s |
| Pydantic | 403 | 8 384 | 0.577 | MEDIUM | 283 | 57.9 s |
| Celery | 371 | 7 546 | 0.578 | MEDIUM | 282 | 30.5 s |
| Flask | 65 | 1 405 | 0.358 | LOW | 18 | 4.7 s |
| drift (self) | 66 | 436 | 0.514 | MEDIUM | 80 | 0.4 s |

Source: [benchmark_results/all_results.json](https://github.com/mick-gsk/drift/blob/main/benchmark_results/all_results.json)

## Recommended Stack

```
Linter (style)        → Ruff, pylint
Type checker (types)  → mypy, pyright
Coherence (drift)     → drift analyze / drift check
Security (SAST)       → Semgrep, CodeQL, SonarQube
```

Drift fills the coherence gap that the other three categories do not cover.

## What Only Drift Sees: The Temporal Layer

Editors like Cursor and VS Code are building native repository intelligence —
they learn what is currently in your codebase. Drift adds a dimension that
no IDE-native or LLM-assisted tool has: **what your code looked like over time**.

Temporal signals are based on git history, not on the current snapshot:

- **Temporal Volatility (TVS):** files accumulating churn from too many authors
  in too short a time — a co-ownership problem invisible to any current-state analysis
- **Co-Change Coupling (CCC):** files that change together but live in separate
  modules — an implicit coupling that no static dependency analysis finds
- **AVS Trend:** whether architecture violations are appearing more frequently
  in recent commits than in older history

When an IDE tells you "this function looks like that one", it sees the snapshot.
Drift sees the trajectory. These are complementary views.

## Drift vs. Ad-hoc LLM Reviews

For solo exploratory work, `git ls-files | xargs cat | claude "find architectural inconsistencies"`
is a valid workflow. No install, no config, immediate output.

Drift is the right choice when you need:

- **Reproducibility:** the same codebase produces exactly the same findings on every run
- **CI integration:** exit codes, SARIF output, GitHub Code Scanning natively
- **Trend tracking:** scores stored across commits, regressions visible over time
- **Compliance evidence:** deterministic, auditable findings with signal references
- **Team consistency:** every developer and every agent sees the same analysis

LLM-based reviews are genuinely useful for ad-hoc exploration. Drift is not
competing with that use case — it is the structured, CI-grade alternative for
teams and regulated environments.

## Further Reading

- [Drift vs Ruff](drift-vs-ruff.md)
- [Drift vs Semgrep and CodeQL](drift-vs-semgrep-codeql.md)
- [Drift vs Architecture Conformance Tools](drift-vs-architecture-conformance.md)
- [Drift vs SonarQube](drift-vs-sonarqube.md)
- [Drift vs GitHub Copilot Code Review](drift-vs-copilot-review.md)
- [Full Benchmark Study](../study.md)
