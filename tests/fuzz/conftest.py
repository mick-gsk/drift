"""Hypothesis profile configuration for drift fuzz tests.

The active profile is controlled via the HYPOTHESIS_PROFILE env var:
- fuzz_fast  (default, for PRs): 100 examples, 5 s deadline
- fuzz_daily (CI daily run):    1000 examples, 30 s deadline
"""

from __future__ import annotations

import os

from hypothesis import HealthCheck, settings

settings.register_profile(
    "fuzz_fast",
    max_examples=100,
    deadline=5_000,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
settings.register_profile(
    "fuzz_daily",
    max_examples=1_000,
    deadline=30_000,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)

settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "fuzz_fast"))
