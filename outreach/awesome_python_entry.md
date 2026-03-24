# Entry for awesome-python

> Repository: https://github.com/vinta/awesome-python
> Section: Code Analysis

## Entry

- [drift](https://github.com/sauremilk/drift) - Architectural coherence analyzer that detects pattern fragmentation, layer violations, and structural erosion in Python codebases using AST and git history analysis.

## PR description (draft)

**Title:** Add drift to Code Analysis section

**Body:**
Adds [drift](https://github.com/sauremilk/drift) to the Code Analysis section.

drift is a static analyzer focused on architectural coherence — it detects structural erosion patterns like pattern fragmentation, architecture violations, and mutant duplicates that accumulate in fast-moving codebases.

- Deterministic analysis (AST + git history), no LLM required
- 7 signal detectors with composite scoring
- Rich terminal, JSON, and SARIF output
- Benchmarked on 15 real-world repos (FastAPI, Django, Pydantic, etc.)
- MIT licensed, Python 3.11+
- PyPI: `pip install drift-analyzer`
