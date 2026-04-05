# Configuration

Create a `drift.yaml` in your project root to customize detection behavior.

## Minimal Example

```yaml
include:
  - "**/*.py"
exclude:
  - "**/node_modules/**"
  - "**/venv/**"
fail_on: none
```

Start with `fail_on: none` so the first rollout teaches the team how to read findings before CI starts blocking merges.

## Full Configuration Reference

```yaml
# File patterns
include:
  - "**/*.py"
exclude:
  - "**/node_modules/**"
  - "**/__pycache__/**"
  - "**/venv/**"

# Signal weights (normalized internally)
weights:
  pattern_fragmentation: 0.22
  architecture_violation: 0.22
  mutant_duplicate: 0.17
  temporal_volatility: 0.17
  explainability_deficit: 0.12
  system_misalignment: 0.10
  doc_impl_drift: 0.00  # Phase 2

# Detection thresholds
thresholds:
  high_complexity: 10
  medium_complexity: 5
  min_function_loc: 10
  similarity_threshold: 0.80
  recency_days: 14
  volatility_z_threshold: 1.5

# Architecture boundaries
policies:
  layer_boundaries:
    - name: "No DB imports in API layer"
      from: "api/**"
      deny_import: ["db.*", "models.*"]
    - name: "No API imports in DB layer"
      from: "db/**"
      deny_import: ["api.*", "routes.*"]

# CI severity gate
fail_on: none
```

## Signal Weights

Weights control the relative importance of each signal in the composite score. They are normalized internally — they don't need to sum to 1.0.

Default weights are calibrated via ablation study (see [Scoring Model](../algorithms/scoring.md)).

## Architecture Policies

Layer boundaries define which imports are allowed between modules. This is the most impactful configuration for the Architecture Violation Signal (AVS).

## Finding Context Policy

Drift classifies each finding into a machine-readable `finding_context` bucket.
Default contexts are:

- `production`
- `fixture`
- `generated`
- `migration`
- `docs`

By default, non-operational contexts (`fixture`, `generated`, `migration`, `docs`)
remain visible in findings, but are excluded from prioritization queues
(`fix_first`, `fix_plan`) unless explicitly enabled.

Example override with glob rules and precedence:

```yaml
finding_context:
  default_context: production
  non_operational_contexts:
    - fixture
    - generated
    - migration
    - docs
  rules:
    - pattern: "**/benchmarks/**"
      context: fixture
      precedence: 40
    - pattern: "**/generated/**"
      context: generated
      precedence: 35
    - pattern: "src/generated/safe/**"
      context: production
      precedence: 50
```

Trade-off: this reduces remediation noise in mixed repositories, but teams with
generated-code ownership should opt in to include non-operational contexts in
prioritization for those workflows.

## Monorepo Configuration Examples

Drift works with any Python repository layout, including monorepos. Two
complementary approaches are available — often used together.

### When to use `--path` vs `include`/`exclude`

| Approach | When to use |
|---|---|
| `--path packages/my_service` | One-off scan of a single package from the command line; no config file changes needed. |
| `include`/`exclude` in `drift.yaml` | Permanent, reviewable configuration committed next to the code; required for CI and multi-package setups. |

Use `--path` for quick ad-hoc analysis. Use `include`/`exclude` when the scope
should be reproducible and versioned.

### Example 1 — Scanning a single package

Place a `drift.yaml` inside the package directory (or at the repo root and
pass `--path` on the command line):

```yaml
# packages/payment_service/drift.yaml
include:
  - "**/*.py"
exclude:
  - "**/tests/**"
  - "**/migrations/**"
  - "**/__pycache__/**"
fail_on: medium
```

Run with:

```bash
drift analyze --repo . --path packages/payment_service
```

Drift restricts file discovery and Git-history analysis to
`packages/payment_service/` so findings from other packages do not appear.

### Example 2 — Scanning multiple packages with shared config

Keep one `drift.yaml` at the repo root that covers all packages but excludes
infrastructure, tooling, and generated code:

```yaml
# drift.yaml (repo root)
include:
  - "packages/**/*.py"
  - "libs/**/*.py"
exclude:
  - "**/tests/**"
  - "**/migrations/**"
  - "**/generated/**"
  - "**/node_modules/**"
  - "**/__pycache__/**"
  - "infra/**"
  - "scripts/**"
fail_on: none
```

Run a single analysis that covers the entire monorepo:

```bash
drift analyze --repo .
```

Or scan individual packages in CI per job:

```bash
drift analyze --repo . --path packages/auth_service
drift analyze --repo . --path packages/payment_service
```

### Example 3 — Per-package `drift.yaml` with package-local overrides

For packages that need stricter or looser thresholds than the default, add a
`drift.yaml` directly inside that package and pass `--path`:

```yaml
# packages/core_lib/drift.yaml
include:
  - "**/*.py"
exclude:
  - "**/tests/**"
thresholds:
  high_complexity: 8       # stricter than default (10)
  similarity_threshold: 0.75
fail_on: high
```

```bash
drift analyze --repo . --path packages/core_lib
```

The local `drift.yaml` is resolved relative to the `--path` argument, so each
package can carry its own policy independent of the repo root.
