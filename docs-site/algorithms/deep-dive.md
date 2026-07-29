# Algorithm Deep Dive

This page explains the core algorithms that power drift's detection pipeline. No LLMs are used — all analysis is deterministic, reproducible, and auditable.

## Pipeline Overview

```text
Repository ──→ File Discovery ──→ AST Parsing ──→ Signals ──→ Scoring ──→ Output
                    │                   │              │           │
              .gitignore +         Python ast     6 independent  Weighted
              drift.yaml          + tree-sitter   signal passes  composite
              glob matching        (optional)     on same data    + dampening
```

## AST Fingerprinting (O(n) per file)

Instead of comparing source text, drift reduces code patterns to **structural fingerprints** — normalized JSON representations of AST subtrees.

### How It Works

1. Parse the file into an AST using Python's `ast` module
2. Walk the tree with a custom `NodeVisitor`
3. Extract **n-grams** (3-grams of node type names), normalizing away identifiers and literals
4. Compute **error-handling fingerprints** for try/except blocks
5. Compute **API endpoint fingerprints** for decorated route handlers

Two functions with identical n-gram multisets but different variable names are structurally identical — exactly what copy-paste-then-modify patterns produce.

**Implementation:** `src/drift/ingestion/ast_parser.py`

## Near-Duplicate Detection (MDS)

The Mutant Duplicate Signal finds functions that are structurally almost identical.

### Three-Phase Approach

**Phase 1: Exact duplicates** — Group by body hash (SHA-256 of normalized AST). O(n).

**Phase 2: Structural near-duplicates** — Bucket functions by LOC (±10%), then compare AST n-gram multisets using Jaccard similarity:

$$J(A, B) = \frac{\sum \min(A_i, B_i)}{\sum \max(A_i, B_i)}$$

Pairs above 0.80 similarity are flagged.

**Phase 3: Semantic near-duplicates** (optional) — FAISS k-NN search with hybrid scoring: `0.6 × jaccard + 0.4 × cosine_embedding`.

## Import Graph Analysis (AVS)

Builds a directed import graph and detects boundary violations.

- **Layer inference** — Files → architectural layers (API=0, Services=1, DB=2)
- **Omnilayer** — Cross-cutting modules exempt from violations
- **Hub dampening** — High-centrality nodes get reduced violation scores
- **Cycle detection** — Tarjan's SCC algorithm, O(n + m)

**Implementation:** `src/drift/signals/architecture_violation.py`

## Count-Dampened Composite Scoring

$$\text{signal\_score} = \overline{s} \times \min\!\left(1,\; \frac{\ln(1 + n)}{\ln(1 + k)}\right)$$

Logarithmic dampening prevents signals with many low-confidence findings from dominating the composite score.

**Implementation:** `src/drift/scoring/engine.py`
