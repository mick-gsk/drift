# Performance

Drift's analysis time depends on repository size (files and functions). This page provides empirical timing data and tuning guidance.

## Benchmark matrix

!!! info "Measurement context"
    Single-threaded, cold start, all 24 signals enabled, embeddings on, default configuration, measured on a single developer workstation. Times include AST parsing, git history extraction, all signal detectors, and scoring. Score column omitted where timing is the primary metric.

| Repository | Files | Functions | Duration (s) | Score |
|-----------|------:|----------:|-------------:|------:|
| sqlmodel | 171 | 399 | 1.4 | — |
| drift (self) pre-ADR-007 | 66 | 436 | 0.4 | — |
| requests | 34 | 670 | 4.9 | — |
| uvicorn | 78 | 790 | 2.8 | — |
| httpx | 60 | 1,134 | 3.6 | — |
| flask | 65 | 1,405 | 4.7 | — |
| starlette | 67 | 1,474 | 4.7 | — |
| drift (self) | 197 | 1,676 | 4.1 | — |
| rich | 176 | 1,790 | 7.8 | — |
| poetry | 437 | 3,109 | 13.3 | — |
| NestJS | 1,667 | 3,472 | 17.5 | — |
| sanic | 296 | 3,641 | 11.3 | — |
| FastAPI | 664 | 3,902 | 13.1 | — |
| pwbs-backend | 484 | 5,057 | 9.3 | — |
| celery | 371 | 7,546 | 30.5 | — |
| pydantic | 399 | 8,350 | 60.7 | — |
| Django | 2,890 | 31,191 | 35.9 | — |

## Scaling characteristics

Analysis time grows roughly as $O(n \times m)$ where $n$ is the number of files and $m$ is the average function count per file. Individual signals have different scaling profiles:

- **AST parsing** (ingestion): linear in files × LOC
- **Pattern fragmentation, mutant duplicates**: quadratic in functions within each module (pairwise comparison), but bounded by module size
- **Temporal volatility, co-change coupling**: linear in git commits × files
- **Embedding-based signals**: dominated by embedding computation, batched by `embedding_batch_size`

## Resource guardrails

Drift includes built-in safety limits:

| Parameter | Default | Config key |
|-----------|---------|------------|
| Max discovered files | 10,000 | `thresholds.max_discovery_files` |
| Embedding batch size | 64 | `embedding_batch_size` |
| ECM max files | 50 | `thresholds.ecm_max_files` |
| ECM lookback commits | 20 | `thresholds.ecm_lookback_commits` |

## Tuning for large repositories

If analysis takes too long, consider these options in order of impact:

1. **Restrict scope:** `drift analyze --path src/core` analyzes only a subdirectory
2. **Use diff mode:** `drift check --diff HEAD~1` analyzes only changed files — typically 10-100× faster
3. **Disable embeddings:** Set `embeddings_enabled: false` in `drift.yaml` — removes the most memory-intensive operation
4. **Lower discovery cap:** Set `thresholds.max_discovery_files` to cap file enumeration
5. **Reduce git depth:** Lower `thresholds.ecm_lookback_commits` for faster co-change analysis

## CI performance

For CI pipelines, `drift check` (diff mode) is the recommended entry point. It analyzes only files changed in the current branch or commit, making it predictably fast regardless of repository size.

Typical CI timings:

- Small PR (1-10 files): < 3 seconds
- Medium PR (10-50 files): 3-10 seconds
- Large PR (50+ files): 10-30 seconds

## Related pages

- [Troubleshooting](../getting-started/troubleshooting.md)
- [Configuration](../getting-started/configuration.md)
