# Demo: Running drift on FastAPI

This walkthrough shows how to analyze the [FastAPI](https://github.com/tiangolo/fastapi) repository with drift.

## Prerequisites

```bash
pip install drift-analyzer   # Python 3.11+
git clone https://github.com/tiangolo/fastapi.git
```

## Full Analysis

```bash
drift analyze --repo fastapi/ --format rich --sort-by impact --max-findings 15
```

### Key options used

| Flag | Purpose |
|------|---------|
| `--repo fastapi/` | Path to the cloned repository |
| `--format rich` | Rich terminal dashboard (default). Alternatives: `json`, `sarif` |
| `--sort-by impact` | Rank findings by structural impact (default). Alternative: `score` |
| `--max-findings 15` | Limit output to top 15 findings (default: 20) |

## CI Gate Mode

```bash
drift check --repo fastapi/ --fail-on high --diff HEAD~1
```

Exits with code 1 if any finding reaches `high` severity or above. Useful in CI pipelines.

## With Configuration File

```bash
drift analyze --repo fastapi/ --config drift.example.yaml
```

See [drift.example.yaml](../drift.example.yaml) for all configuration options including:
- `include` / `exclude` glob patterns
- Signal weights (PFS, AVS, MDS, EDS, TVS, SMS, DIA)
- Layer boundary policies (e.g. deny `db.*` imports from `api/`)
- Similarity and complexity thresholds

## Additional Options

```bash
# JSON output for programmatic consumption
drift analyze --repo fastapi/ --format json > findings.json

# SARIF output for GitHub Code Scanning integration
drift analyze --repo fastapi/ --format sarif > results.sarif

# Restrict analysis to a subdirectory
drift analyze --repo fastapi/ --path fastapi/routing

# Limit git history window
drift analyze --repo fastapi/ --since 30

# Parallel parsing (auto-detected, but can be set explicitly)
drift analyze --repo fastapi/ --workers 4

# Show suppressed findings (via drift:ignore comments)
drift analyze --repo fastapi/ --show-suppressed
```

## Expected Finding Types

Based on drift's 7 signal detectors, a large framework like FastAPI typically surfaces:

| Signal | Code | What it detects |
|--------|------|-----------------|
| Pattern Fragmentation | PFS | Same concern implemented multiple ways (e.g. error handling, validation) |
| Architecture Violation | AVS | Imports crossing layer boundaries |
| Mutant Duplicates | MDS | Near-identical code blocks with minor variations |
| Explainability Deficit | EDS | Complex functions lacking docstrings or comments |
| Temporal Volatility | TVS | Files with unusually high churn in recent history |
| System Misalignment | SMS | Modules whose structure diverges from project conventions |
| Doc-Implementation Drift | DIA | Gaps between documentation and actual code behavior |

## Other Commands

```bash
# View patterns catalog
drift patterns

# Timeline view per module
drift timeline --repo fastapi/

# Score trend over time
drift trend --repo fastapi/

# Generate shields.io badge URL
drift badge --repo fastapi/

# Self-analysis (run drift on itself)
drift self
```
