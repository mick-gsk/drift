# FAQ

## What is drift?

Drift is a deterministic static analyzer for architectural erosion and cross-file coherence problems in Python repositories.

## What does drift detect?

Drift detects six scoring signal families: pattern fragmentation, architecture violations, mutant duplicates, explainability deficit, temporal volatility, and system misalignment. DIA is visible as a report-only signal with weight 0.00.

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

## Does drift use an LLM in the detector pipeline?

No. The detector path is deterministic.

See [Trust and Evidence](trust-evidence.md) and [Benchmarking and Trust](benchmarking.md).

## What is the drift composite score?

A weighted aggregate of six signal scores (PFS, AVS, MDS, EDS, TVS, SMS) that produces a single number between 0 and 1. Higher values indicate more structural erosion. DIA is excluded from the composite score (weight 0.00).

See [Scoring Model](algorithms/scoring.md).

## How precise are drift's findings?

97.3% strict precision across 263 ground-truth-labeled findings on 15 repositories (v0.3). All false positives came from a single signal (DIA) that carries zero scoring weight.

See [Benchmarking and Trust](benchmarking.md) and [STUDY.md](https://github.com/sauremilk/drift/blob/master/STUDY.md).

## Can drift detect dependency cycles in Python?

Yes. The AVS signal detects circular dependencies (A→B→C→A) and upward imports that cross inferred or configured layer boundaries.

## Does drift support monorepos?

Yes. Drift analyzes any Python repository structure. For monorepos, you can use `--path` to restrict analysis to a subdirectory or configure `include`/`exclude` patterns in `drift.yaml`.

## How does drift compare to SonarQube, pylint, or Semgrep?

Drift complements those tools. Linters catch style violations, type checkers catch type errors, security scanners catch vulnerabilities. Drift catches cross-file architectural coherence problems that none of those tools model.

See [Comparisons](comparisons/index.md).