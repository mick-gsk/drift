# Show HN: Drift — Detect architectural erosion in AI-assisted codebases

**URL:** https://github.com/sauremilk/drift

## Post text

AI code generation is fast — but speed hides structural problems. When
Copilot or ChatGPT repeatedly generates slightly different implementations
of the same concern, you end up with pattern fragmentation, copy-paste
variants, and layer violations that no linter catches.

**Drift** is a deterministic static analyzer for architectural coherence.
No LLM, no cloud, no magic. It parses your AST and git history, runs
7 signal detectors (pattern fragmentation, architecture violations,
mutant duplicates, explainability deficit, temporal volatility, system
misalignment, doc-implementation drift), and produces a composite score
with actionable findings.

```
pip install drift-analyzer
drift analyze --repo .
```

Results come in three formats: Rich terminal dashboard, JSON, or SARIF
(for GitHub Code Scanning integration). Works as a CI gate:

```
drift check --fail-on high
```

Benchmarked on FastAPI, Django, Pydantic and 12 more real-world repos.
97.3% precision on 2,642 findings across 15 projects.

Currently Python-only (TypeScript experimental). Open source, MIT licensed.

Would appreciate feedback on the signal design and whether the findings
are actionable in your projects.
