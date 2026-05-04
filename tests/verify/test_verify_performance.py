"""Latency regression test for verify() — must complete within 180 s (SC-001).

Skipped by default; run with: pytest -m slow --run-slow
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

LATENCY_LIMIT_S = 180.0


@pytest.mark.slow
def test_verify_completes_within_latency_limit(tmp_path: Path) -> None:
    """End-to-end verify() call must complete within 180 s (SC-001)."""
    from drift_verify._models import ChangeSet
    from drift_verify._promoter import PatternHistoryStore
    from drift_verify._verify import verify

    diff_text = "\n".join(
        [f"--- a/src/file_{i}.py\n+++ b/src/file_{i}.py\n@@ -1 +1 @@\n-x\n+y" for i in range(10)]
    )
    cs = ChangeSet(diff_text=diff_text, repo_path=tmp_path)
    store = PatternHistoryStore(tmp_path / ".drift" / "pattern_history.jsonl")

    start = time.monotonic()
    _pkg = verify(cs, use_reviewer=False, history_store=store)
    elapsed = time.monotonic() - start

    assert elapsed < LATENCY_LIMIT_S, (
        f"verify() took {elapsed:.1f}s — exceeds SC-001 limit of {LATENCY_LIMIT_S}s"
    )
