# Twitter/X thread — drift launch (5 tweets)

---

**1/5**
AI code generation is fast. But speed hides structural problems.

Over weeks, your codebase quietly accumulates:
→ Same concern implemented 3 different ways
→ Copy-paste variants everywhere
→ Imports crossing layer boundaries

No linter catches this. So I built something that does.

---

**2/5**
Meet drift — a deterministic static analyzer for architectural coherence.

No LLM. No cloud. Just AST parsing + git history.

7 signal detectors: pattern fragmentation, architecture violations, mutant duplicates, explainability deficit, temporal volatility, system misalignment, doc drift.

```
pip install drift-analyzer
drift analyze --repo .
```

---

**3/5**
Benchmarked on 15 real-world repos:
- FastAPI, Django, Pydantic, httpx, Flask, Starlette…
- 2,642 findings analyzed
- 97.3% precision
- 86% recall on controlled mutations

Full evaluation study with methodology:
github.com/sauremilk/drift/blob/master/STUDY.md

---

**4/5**
Works as a CI gate:

```
drift check --fail-on high --diff HEAD~1
```

Outputs: Rich terminal, JSON, or SARIF (plugs into GitHub Code Scanning).

GitHub Action template included. Pre-commit hook supported.

---

**5/5**
Open source, MIT licensed, Python 3.11+.
TypeScript support is experimental.

Try it:
→ github.com/sauremilk/drift
→ Docs: sauremilk.github.io/drift/

Feedback welcome — especially on false positive rates in your projects.
