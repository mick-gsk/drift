# Case Studies

Drift has been benchmarked on real-world open-source repositories to validate its detection signals. These case studies show what drift finds — and what those findings mean for maintainability.

## Repositories Analyzed

!!! info "Benchmark context"
    Full-clone analysis (all branches and tests included), default configuration, Drift v2.5.x, April 2026. The [Comparisons](../comparisons/index.md) page uses a narrower `src/`-only scope and shows different file counts and scores for the same repositories.

| Repository | Files | Functions | Drift Score | Time |
|---|---|---|---|---|
| [FastAPI](fastapi.md) | 1,118 | 4,554 | 0.690 HIGH | 2.3s |
| [Pydantic](pydantic.md) | 403 | 8,384 | 0.577 MEDIUM | 57.9s |
| [Django](django.md) | — | — | 0.535–0.563 | — |
| [Paramiko](paramiko.md) | 55 | 962 | 0.468 MEDIUM | 5.8s |
| httpx | 60 | 1,134 | 0.472 MEDIUM | 3.3s |
| drift (self) | 45 | 263 | 0.442 MEDIUM | 0.3s |
