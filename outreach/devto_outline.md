# dev.to article outline — Detecting Architectural Erosion in AI-Assisted Codebases

## Title
**Detecting Architectural Erosion in AI-Assisted Codebases with Drift**

## Tags
`python`, `codequality`, `architecture`, `opensource`

---

## Outline

### 1. The problem (300 words)
- AI assistants generate correct code fast, but each generation is independent
- Over time: pattern fragmentation, duplicate variants, boundary violations
- Traditional tools (linters, type checkers) don't catch coherence problems
- Example: 3 different error handling patterns in one project, each valid individually

### 2. What is architectural drift? (200 words)
- Definition: gradual loss of structural coherence
- Not bugs — the code works. But it gets harder to maintain
- Analogy: code entropy — disorder increases without active effort
- Why it matters more with AI: faster generation means faster accumulation

### 3. Introducing drift (300 words)
- Deterministic static analyzer, no LLM, no cloud
- 7 signal detectors: PFS, AVS, MDS, EDS, TVS, SMS, DIA
- Pipeline: AST parsing + git history → signal detection → scoring → output
- Install and run in 2 lines:
  ```bash
  pip install drift-analyzer
  drift analyze --repo .
  ```

### 4. How the signals work (500 words)
- Walk through each of the 7 signals with a concrete example
- PFS: difflib-based similarity detection on error handling blocks
- AVS: import graph analysis against configurable layer boundaries
- MDS: AST-level near-duplicate detection
- Show one real finding from a case study (FastAPI or Pydantic)

### 5. CI integration (200 words)
- `drift check --fail-on high --diff HEAD~1`
- SARIF output for GitHub Code Scanning
- Example GitHub Action (link to `examples/drift-check.yml`)
- Pre-commit hook usage

### 6. Evaluation results (200 words)
- 15 real-world repos, 2,642 findings
- 97.3% precision, 86% recall on mutations
- Link to full study (STUDY.md)

### 7. Limitations and roadmap (150 words)
- Currently Python-focused (TypeScript experimental)
- DIA signal precision needs improvement
- Not a replacement for linters or security scanners
- Complements existing tooling

### 8. Try it yourself (100 words)
- GitHub: https://github.com/sauremilk/drift
- Docs: https://sauremilk.github.io/drift/
- Example project with intentional drift: `examples/demo-project/`

---

## Estimated length
~2,000 words + code blocks

## Call to action
Try it on your repo and share findings in the comments.
