"""Smoke test: scripts/check_model_consistency.py exits 0 for current repo state."""

from __future__ import annotations

import subprocess
import sys


def test_model_consistency_check_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_model_consistency.py"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"check_model_consistency.py failed:\n{result.stdout}\n{result.stderr}"
    )
