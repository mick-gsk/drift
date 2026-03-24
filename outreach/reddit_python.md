# r/Python post — drift: static analyzer for architectural coherence

**Title:** drift — detect architectural erosion from AI-generated code (deterministic, no LLM)

**Body:**

I built [drift](https://github.com/sauremilk/drift), a static analyzer that
detects structural coherence problems in Python codebases — the kind of issues
that accumulate when AI assistants generate code faster than teams can review it.

## What it does

Drift parses your AST and git history to run 7 detectors:

- **PFS** — Pattern Fragmentation: same concern implemented multiple ways
- **AVS** — Architecture Violations: imports crossing layer boundaries
- **MDS** — Mutant Duplicates: near-identical code with minor variations
- **EDS** — Explainability Deficit: complex code without documentation
- **TVS** — Temporal Volatility: high-churn files in recent history
- **MDS** — System Misalignment: modules diverging from project conventions
- **DIA** — Doc-Implementation Drift: docs don't match the code

Each finding gets a severity, affected location, and a next-step recommendation.

## Quickstart

```bash
pip install drift-analyzer   # Python 3.11+
drift analyze --repo .
```

Output: Rich terminal dashboard, JSON, or SARIF. CI mode:

```bash
drift check --fail-on high --diff HEAD~1
```

## Benchmarks

Evaluated on 15 real-world repos (FastAPI, Django, Pydantic, httpx, etc.).
97.3% precision on 2,642 findings. 86% recall on controlled mutation tests.
Full study: https://github.com/sauremilk/drift/blob/master/STUDY.md

## Technical details

- Deterministic — no LLM, no network calls
- AST-based with parallel parsing
- Configurable signal weights and layer policies (YAML config)
- SARIF output for GitHub Code Scanning
- GitHub Action included
- MIT licensed

Feedback welcome — especially on false positive rates in your codebases.

GitHub: https://github.com/sauremilk/drift
