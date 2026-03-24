# Entry for awesome-static-analysis

> Repository: https://github.com/analysis-tools-dev/static-analysis
> Section: Python

## Entry

- [drift](https://github.com/sauremilk/drift) — Detects architectural erosion in Python codebases. Analyzes AST and git history to find pattern fragmentation, architecture violations, mutant duplicates, and 4 more coherence signals. Deterministic, no LLM required. SARIF output for CI integration.

## PR description (draft)

**Title:** Add drift — architectural coherence analyzer for Python

**Body:**
Adds [drift](https://github.com/sauremilk/drift) to the Python section.

drift is a deterministic static analyzer that detects architectural coherence problems — pattern fragmentation, layer boundary violations, near-duplicate code, and more. It complements linters and type checkers by surfacing structural erosion patterns.

- 7 signal detectors (PFS, AVS, MDS, EDS, TVS, SMS, DIA)
- Output formats: Rich terminal, JSON, SARIF
- Benchmarked on 15 real-world repos (97.3% precision)
- MIT licensed, Python 3.11+

Checklist:
- [x] Tool is open source
- [x] README with installation and usage instructions
- [x] Actively maintained
- [x] Evaluation data available (STUDY.md)
