# Defect Corpus

This directory documents the methodology for the drift **external-ground-truth defect corpus**.

## What this is

The defect corpus is a curated set of synthetic code samples that reproduce confirmed,
real-world bug classes.  Each entry is backed by a publicly linkable external source
(GitHub issue, CVE, OWASP catalogue entry) that independently attests the pattern as a
real defect — not a heuristic invented in-house.

Running drift against these samples measures **recall against external ground truth**:
*could drift have detected this class of bug before the fix was merged?*

## File locations

| Resource | Path |
|---|---|
| Entry definitions + schema | `tests/fixtures/defect_corpus.py` |
| pytest recall tests | `tests/test_defect_corpus.py` |
| Standalone benchmark script | `scripts/defect_corpus_benchmark.py` |
| Generated recall artefact | `benchmark_results/defect_corpus_recall.json` |

## Scope and limitations

### What the corpus covers

- **Structural signal correlates of confirmed bugs.**  Every entry maps to a drift
  signal (e.g. `circular_import`, `broad_exception_monoculture`, `mutant_duplicate`).
  The entry tests whether that signal fires on a synthetic pre-fix codebase.

### What the corpus does NOT cover

- **Runtime logic bugs without structural correlate.**  An off-by-one error inside
  a pure function has no structural drift signal; it will not appear here.
- **Precision claims.**  The corpus is recall-only.  A "detected" result means drift
  fires a signal on the synthetic fixture; it does not guarantee that all real
  instances of the pattern are caught, nor that the finding is always a true positive.
- **Bug reproduction for exploitation.**  No entry contains exploit code, working
  credentials, or any material that could be used as an attack vector.

## Copyright and attribution policy

Every entry in the corpus is a **transformative reproduction**:

1. The narrative of the bug class (what went wrong, why) comes from a public source.
2. The code is **independently authored** — no verbatim copying of original source.
3. Function names, module names, and variable names are all original.
4. The `evidence_url` field cites the public source for auditability.
5. The `inspired_by_note` field on each entry explicitly records the transformative nature.

This approach is consistent with fair use / fair dealing norms for educational and
research purposes and avoids any copyright concern from original project authors.

## Adding entries

To add a new corpus entry:

1. Find a publicly confirmed bug (merged fix PR, CVE, issue closed as `type:bug`).
2. Identify the drift signal whose pattern class best matches the bug.
3. Write a minimal synthetic codebase (`files` dict) in the pre-fix state.
4. Add a `DefectCorpusEntry` to `tests/fixtures/defect_corpus.py` and append it to
   `ALL_DEFECT_CORPUS`.
5. Run `pytest tests/test_defect_corpus.py -v --tb=short` to verify the signal fires.
6. Run `python scripts/defect_corpus_benchmark.py --verbose` to regenerate the artefact.

Minimum requirements per entry:

- `evidence_url` must be a stable public URL (not a private issue, not a personal blog).
- `inspired_by_note` must explicitly state the transformative nature.
- At least one `ExpectedFinding` with `should_detect=True`.
- The synthetic code must be minimal (< 50 lines per file) and self-contained.

## Minimum recall gate

The pytest suite enforces a minimum overall recall of **0.70** (70 %).  This leaves room
for confirmed bug classes that do not yet have a matching drift signal, while preventing
silent degradation of existing coverage.  Raise the gate in increments of 0.05 as new
signals are added.
