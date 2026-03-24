# r/ExperiencedDevs post — Architectural erosion from AI-assisted development

**Title:** How do you monitor architectural coherence in AI-accelerated codebases?

**Body:**

Our team noticed a pattern: since adopting AI code assistants, the individual
diffs look fine — they pass linters, type checkers, and tests. But over weeks,
the codebase accumulates structural problems that are hard to spot in review:

- Error handling implemented three different ways across modules
- Copy-paste variants of the same validation logic
- Imports crossing architectural boundaries that were meant to be enforced
- Documentation drifting from actual behavior

These aren't bugs. They're coherence problems that compound over time and make
the codebase harder to reason about.

I built [drift](https://github.com/sauremilk/drift) to surface these patterns
automatically. It's a deterministic static analyzer (no LLM) that parses the
AST and git history to detect 7 types of architectural erosion:

1. Pattern fragmentation — same concern, multiple implementations
2. Architecture violations — imports crossing defined layer boundaries
3. Mutant duplicates — near-identical code with trivial variations
4. Explainability deficit — complex code without documentation
5. Temporal volatility — churn hotspots
6. System misalignment — modules diverging from conventions
7. Doc-implementation drift — documentation vs. code gaps

We've benchmarked it on 15 open-source projects (FastAPI, Django, Pydantic, etc.)
with 97.3% precision on 2,642 findings.

```bash
pip install drift-analyzer
drift analyze --repo .
drift check --fail-on high   # CI mode
```

Curious whether others are seeing similar erosion patterns and how you're
dealing with them. The tool is open source (MIT):
https://github.com/sauremilk/drift

Full evaluation study: https://github.com/sauremilk/drift/blob/master/STUDY.md
