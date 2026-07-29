"""Tests for the latency measurement harness (gate G1)."""

import sys

from scripts.gates.measure_latency import measure


def test_measure_returns_percentiles_for_a_trivial_command():
    result = measure([sys.executable, "-c", "pass"], runs=5)

    assert result["runs"] == 5
    assert result["failures"] == 0
    assert result["min_ms"] <= result["p50_ms"] <= result["p95_ms"] <= result["max_ms"]
    assert result["p95_ms"] > 0


def test_measure_counts_failures_without_raising():
    result = measure([sys.executable, "-c", "raise SystemExit(3)"], runs=3)

    assert result["failures"] == 3
