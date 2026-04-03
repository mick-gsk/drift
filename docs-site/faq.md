# FAQ

## What is drift?

Drift is a deterministic static analyzer for architectural erosion and cross-file coherence problems in Python repositories.

## What does drift detect?

Drift detects 15 signal families across structural, architectural, and temporal dimensions. Five core scoring signals are currently active in the composite score: pattern fragmentation (PFS), architecture violations (AVS), mutant duplicates (MDS), explainability deficit (EDS), and system misalignment (SMS). Temporal volatility (TVS) currently runs in report-only mode while it is re-validated. Additional scoring-active signals include DIA, BEM, TPD, GCD, NBV, BAT, ECM, COD (v0.7.3), and CCC (v0.8.0).

See [Signal Reference](algorithms/signals.md).

## Is drift a bug finder or security scanner?

No. Drift is not positioned as a bug finder, a security scanner, or a type checker.

For those problems, use the dedicated tools already built for them.

## Why would a team use drift next to Ruff, Semgrep, or CodeQL?

Because those tools do not primarily model cross-file architectural coherence.

See [Drift vs Ruff](comparisons/drift-vs-ruff.md) and [Drift vs Semgrep and CodeQL](comparisons/drift-vs-semgrep-codeql.md).

## When should a team not use drift?

Avoid using drift as a first-day hard gate on tiny repositories or when the real need is bug detection, security review, or type-safety enforcement.

## How should a team introduce drift?

Start locally, then move to report-only CI, then gate only on `high` findings after reviewing real output.

See [Team Rollout](getting-started/team-rollout.md).

## Why does PyPI still classify drift as Alpha?

Because the project uses a conservative release signal.

The core Python analysis and the CI/SARIF rollout path are the most stable parts of drift today, but TypeScript support remains experimental, embeddings-based parts are optional and experimental, and the benchmark methodology is still evolving.

See [Stability and Release Status](stability.md).

## Does drift use an LLM in the detector pipeline?

No. The detector path is deterministic.

See [Trust and Evidence](trust-evidence.md) and [Benchmarking and Trust](benchmarking.md).

## What is the drift composite score?

A weighted aggregate of all 15 signal scores that produces a single number between 0 and 1. Higher values indicate more structural erosion. Auto-calibration rebalances weights at runtime based on finding distribution.

See [Scoring Model](algorithms/scoring.md).

## How precise are drift's findings?

97.3% strict precision across 263 ground-truth-labeled findings on 15 repositories (v0.3). All false positives came from a single signal (DIA) that carries zero scoring weight.

See [Benchmarking and Trust](benchmarking.md) and [STUDY.md](https://github.com/sauremilk/drift/blob/main/docs/STUDY.md).

## Can drift detect dependency cycles in Python?

Yes. The AVS signal detects circular dependencies (A→B→C→A) and upward imports that cross inferred or configured layer boundaries.

## Does drift support monorepos?

Yes. Drift analyzes any Python repository structure. For monorepos, you can use `--path` to restrict analysis to a subdirectory or configure `include`/`exclude` patterns in `drift.yaml`.

## How does drift compare to SonarQube, pylint, or Semgrep?

Drift complements those tools. Linters catch style violations, type checkers catch type errors, security scanners catch vulnerabilities. Drift catches cross-file architectural coherence problems that none of those tools model.

See [Comparisons](comparisons/index.md).