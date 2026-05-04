# Drift

A static-analysis tool that measures architectural erosion in Python (and
TypeScript) codebases via a set of Signals, aggregates them into a Composite
Score, and emits actionable Findings for humans and agents.

## Language

**Signal**:
A single measurable indicator of architectural erosion. Each signal has a
unique ID (e.g. `PFS`, `AVS`, `MDS`), a scope (`file_local` or
`cross_file`), and emits zero or more Findings.
_Avoid_: metric, check, rule, detector.

**Finding**:
One emitted result from a Signal run, carrying `severity`, `reason`, and
`next_action`. Findings are the machine-readable output agents and humans act on.
_Avoid_: issue, warning, result, alert.

**Composite Score**:
The weighted aggregation of all active Signal scores for a repository or
file. Ranges 0–100; lower is worse.
_Avoid_: total score, final score, overall score.

**Ingestion**:
The pipeline stage that discovers files, parses AST and git history, and
produces the data model (FileRecord, HistoryRecord) that Signals consume.
_Avoid_: parsing, scanning (reserve `scan` for the `drift scan` CLI command).

**Gate**:
A pre-push or pre-commit enforcement check that blocks progress when a
policy condition is not met (e.g. missing evidence artifact, failing
audit freshness check).
_Avoid_: guard, check (use `check` only for `make check`), hook (use
`hook` only for git-hook mechanics).

**Session**:
An MCP-managed stateful interaction context that persists signal baselines,
replay queues, guardrail decisions, and handover artifacts across multiple
agent turns.
_Avoid_: conversation, run, context.

**Nudge**:
A fast post-edit regression check (`drift_nudge`) that re-runs only
file-local Signals against changed files to detect immediate degradation.
Distinguished from a full Scan by its <1 s latency target.
_Avoid_: quick scan, fast check.

**Baseline**:
A stored Composite Score snapshot used by Nudge and Diff to measure
direction of change (`improving` / `stable` / `degrading`).
_Avoid_: reference score, previous score.

**Scan** (`drift scan` / `drift_scan`):
A full analysis run across the entire repository, computing all Signals
including cross-file scope. Slower than a Nudge; produces the authoritative
Composite Score.
_Avoid_: analysis (reserve for `drift analyze`), full run.

**Brief** (`drift_brief`):
A concise, agent-readable summary of the current architectural state of a
file or directory, derived from a Scan.
_Avoid_: summary, overview, report.

**Evidence Artifact**:
A versioned JSON file under `benchmark_results/` that records precision,
recall, and test results for a `feat:` commit. Required by Gate 2b before push.
_Avoid_: benchmark file, result file.

**ADR** (Architecture Decision Record):
A short document under `docs/decisions/` recording that a hard-to-reverse
architectural decision was made, why, and what alternatives were considered.
Status: `proposed` → `accepted` | `rejected` | `superseded`.
_Avoid_: design doc, decision note.

## Relationships

- A **Scan** runs N **Signals** over the output of one **Ingestion**.
- Each **Signal** emits 0..N **Findings** per file or repo.
- All Signal scores are aggregated into one **Composite Score**.
- A **Nudge** re-runs only `file_local` Signals against changed files;
  `cross_file` Signals are estimated from the last **Baseline**.
- A **Session** holds one active **Baseline** and a replay queue of
  prior Scan results.
- A **Gate** validates that **Evidence Artifacts** and audit freshness
  are in sync with the current commit before push is allowed.

## Example dialogue

> **Dev:** "The Nudge shows direction `degrading` — should I revert?"
> **Maintainer:** "Check `revert_recommended` first. If `true` and `safe_to_commit: false`, revert. If just `degrading` but `safe_to_commit: true`, the Finding may still be worth fixing before push."

> **Dev:** "Why did Gate 2b fail?"
> **Maintainer:** "A `feat:` commit requires a versioned Evidence Artifact in `benchmark_results/`. Run `make generate_feature_evidence` to produce it."

## Flagged ambiguities

- "scan" vs. "analyze": `drift scan` is the CLI subcommand for a targeted
  file-set scan; `drift analyze` is the full-repo analysis. Do not use
  interchangeably.
- "signal" vs. "check": signal is the Drift-specific term; avoid "check"
  as a synonym to prevent confusion with `make check` (the CI target).
