# Feature 05 — drift_nudge Cold-Start Profiling (Before)

**Date**: 2026-04-21
**Author**: Automated via Feature-05 prompt
**Baseline measurement**: `benchmark_results/mcp_performance_smoke.json`

---

## Measured Cold-Start Latency

| Tool | mean_seconds | corpus |
|------|-------------|--------|
| `drift_nudge` | **4.687 s** | benchmarks/corpus (~1000 files) |
| `drift_scan` | 1.203 s | benchmarks/corpus |
| `drift_brief` | 0.110 s | benchmarks/corpus |

Conditions: `iterations=1, warmup=0` → no in-memory baseline, no persisted disk baseline.
Target: < 1.0 s.

---

## Code-Level Root-Cause Analysis

Bottleneck is in `src/drift/api/nudge.py` → `_NudgeExecution._create_baseline()`.
The method performs **three separate passes** over the file list:

### Pass 1 — standalone `discover_files()` (~100 ms)
```python
all_files = discover_files(self.repo_path, include=cfg.include, ...)
```
Discovers the same file list that `analyze_repo()` will internally discover again in Pass 2.

### Pass 2 — `analyze_repo()` (~1.2 s)
```python
analysis = analyze_repo(self.repo_path, config=cfg)
```
Internally: discovers files + reads+hashes every file + parses every file + runs all signals.
`ParsedInputs.file_hashes` (already computed) is **discarded** before `RepoAnalysis` is returned.

### Pass 3 — second I/O loop (~3.5 s bottleneck)
```python
for finfo in all_files:
    h = ParseCache.file_hash(full_path)   # re-reads full file content  (~1000 reads)
    file_hashes[posix] = h
    cached_pr = pcache.get(h)             # reads per-file JSON from .drift-cache/  (~1000 reads)
    if cached_pr: parse_map[posix] = cached_pr; continue
    pr = parse_file(...)                  # re-parses if not cached
```

This is **pure duplication**: `analyze_repo()` already computed `file_hashes` inside
`IngestionPhase.run()` (see `pipeline.py:ParsedInputs.file_hashes`) and already populated
the on-disk parse cache. Pass 3 discards that work and repeats ~2000 I/O operations.

---

## Time Breakdown Estimate

| Phase | Estimated cost |
|-------|---------------|
| Pass 1: `discover_files()` | ~100 ms |
| Pass 2: `analyze_repo()` | ~1.2 s |
| Pass 3: `ParseCache.file_hash()` × 1000 | ~1.8 s (file content reads) |
| Pass 3: `pcache.get()` × 1000 | ~1.6 s (JSON reads from cache dir) |
| **Total** | **~4.7 s** |

---

## Fix Strategy

Surface `ParsedInputs.file_hashes` (already computed in `IngestionPhase.run()`) back to
`_create_baseline()` via an optional `file_hashes_out: dict[str, str] | None` parameter on:

1. `AnalysisPipeline.run()` (`pipeline.py`)
2. `_run_pipeline()` (`analyzer.py`)
3. `analyze_repo()` (`analyzer.py`)

In `_create_baseline()`:
- Remove Pass 1 (standalone `discover_files()`)
- Remove Pass 3 (entire I/O loop)
- Pass `file_hashes_out=file_hashes` to `analyze_repo()` to get hashes from pipeline
- Return `parse_map = {}` (empty, same as disk warm-load path — already works in `IncrementalSignalRunner`)

**Expected savings**: ~3.5 s (Pass 3 eliminated) + ~100 ms (Pass 1 eliminated)
**Expected cold-start after fix**: ~1.2 s

Note: If further below 1 s is needed, additional optimization (e.g. skip git history in nudge
baseline creation via `since_days=0`) can reduce the pipeline cost.

---

## Correctness Proof

Empty `parse_map = {}` is the already-accepted behavior for disk warm-loads:
- `BaselineManager._load_persisted_nudge_baseline()` returns `(baseline, findings, {})` from disk
- `IncrementalSignalRunner.run()` starts with `merged = dict(self._baseline_parse_map)` — works with empty dict
- `_parse_single_changed_file()` uses `baseline_parse_map.get(fp)` — gracefully handles None

Citations: `src/drift/incremental.py` lines ~550, ~720
