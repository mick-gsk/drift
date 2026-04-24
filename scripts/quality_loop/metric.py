"""Composite quality metric combining drift_score, ruff, and mypy."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class MetricResult:
    composite: float
    drift_score: float
    ruff_count: int
    mypy_count: int
    duration_ms: float

    def __str__(self) -> str:
        return (
            f"composite={self.composite:.4f} "
            f"(drift={self.drift_score:.4f}, "
            f"ruff={self.ruff_count}, "
            f"mypy={self.mypy_count})"
        )


@dataclass
class CompositeMetric:
    repo_root: Path
    src_path: Path | None = None
    # Weights must sum to 1.0.
    # Ruff/mypy dominate because the AST-level transforms can only affect
    # style violations — the drift_score (architectural erosion) is invariant
    # to these transforms and acts as a passive constraint, not a reward signal.
    weight_drift: float = 0.1
    weight_ruff: float = 0.7
    weight_mypy: float = 0.2
    # Baseline ruff/mypy counts for normalisation — set on first call
    _ruff_baseline: int = field(default=0, init=False, repr=False)
    _mypy_baseline: int = field(default=0, init=False, repr=False)
    _baseline_set: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        # Default src_path to repo_root so ruff/mypy are never invoked with
        # str(None) = "None" as the target path.
        if self.src_path is None:
            self.src_path = self.repo_root

    def measure(self) -> MetricResult:
        import time

        t0 = time.perf_counter()
        drift_score = self._run_drift()
        ruff_count = self._run_ruff()
        mypy_count = self._run_mypy()
        duration_ms = (time.perf_counter() - t0) * 1000

        if not self._baseline_set:
            self._ruff_baseline = max(ruff_count, 1)
            self._mypy_baseline = max(mypy_count, 1)
            self._baseline_set = True

        ruff_norm = ruff_count / self._ruff_baseline
        mypy_norm = mypy_count / self._mypy_baseline

        composite = (
            self.weight_drift * drift_score
            + self.weight_ruff * ruff_norm
            + self.weight_mypy * mypy_norm
        )

        return MetricResult(
            composite=composite,
            drift_score=drift_score,
            ruff_count=ruff_count,
            mypy_count=mypy_count,
            duration_ms=duration_ms,
        )

    def _run_drift(self) -> float:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "drift",
                "analyze",
                "--repo",
                str(self.repo_root),
                "--format",
                "json",
                "--exit-zero",
            ],
            capture_output=True,
            text=True,
            cwd=self.repo_root,
        )
        if result.returncode != 0 and not result.stdout:
            return 1.0  # treat failure as worst-case score

        raw = result.stdout.strip()
        # Strip trailing non-JSON console output (Rich symbols etc.)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            return 1.0

        try:
            data = json.loads(raw[start:end])
        except json.JSONDecodeError:
            return 1.0

        return float(data.get("drift_score", data.get("composite_score", 1.0)))

    def _run_ruff(self) -> int:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                str(self.src_path),
                "--output-format",
                "json",
                "--quiet",
            ],
            capture_output=True,
            text=True,
            cwd=self.repo_root,
        )
        if not result.stdout:
            return 0
        try:
            findings = json.loads(result.stdout)
            return len(findings)
        except json.JSONDecodeError:
            return 0

    def _run_mypy(self) -> int:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "mypy",
                str(self.src_path),
                "--no-error-summary",
                "--ignore-missing-imports",
                "--no-incremental",
            ],
            capture_output=True,
            text=True,
            cwd=self.repo_root,
        )
        lines = result.stdout.splitlines()
        # Count lines that look like errors/warnings (contain ": error:" or ": warning:")
        return sum(1 for line in lines if ": error:" in line or ": warning:" in line)
