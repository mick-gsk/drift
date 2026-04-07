# Case Study: Paramiko

**Repository:** [paramiko/paramiko](https://github.com/paramiko/paramiko)
**Stats:** 55 files, 962 functions
**Drift Score:** 0.468 (MEDIUM) | **Time:** 5.8s

## Key Findings

### 5 God Module Candidates (AVS)

Paramiko's core contains five modules with high coupling that concentrate responsibilities: `transport.py` (Ca=3, Ce=35), `util.py` (Ca=22, Ce=8), `common.py` (Ca=27, Ce=2), `pkey.py` (Ca=6, Ce=18), and `message.py` (Ca=17, Ce=5). Of these, `transport.py` has the highest impact — a single change there ripples across 3 dependent modules.

This is the classic "god module" pattern in long-lived protocol libraries: core transport logic grows over years as features are added, but responsibility boundaries are never split.

### 18 Circular Import Chains (CIR)

Drift detected 18 circular import chains, the longest involving 6 modules: `paramiko → packet → util → hostkeys → pkey → message → paramiko`. These cycles indicate tangled module responsibilities and can cause subtle runtime `ImportError`s depending on import order.

### 54 Unexplained High-Complexity Functions (EDS)

The Explainability Deficit Signal flagged 54 functions with high cyclomatic complexity but no docstrings. The top three are `Transport.run`, `SSHClient.connect`, and `BufferedFile.readline` — all critical protocol-handling functions.

## Interpretation

Paramiko is a mature, stable SSH library — but stability has come at the cost of architectural clarity. The god-module pattern in `transport.py` and the circular import chains create a high blast radius for changes and make contributor onboarding difficult.

**Recommendation:** Start with `transport.py` — extract protocol state management into a separate module to reduce coupling. For the circular imports, introduce a shared types module and use `TYPE_CHECKING`-guarded imports to break the longest chains first.
