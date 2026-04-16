"""Regression test for Issue #369: silent exception swallowing in precision.py.

Verifies that when a signal raises during precision evaluation, the error is
surfaced as a RuntimeWarning and as an AnalyzerWarning in the returned list
rather than being silently discarded.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from drift.precision import ensure_signals_registered, run_fixture
from tests.fixtures.ground_truth import ALL_FIXTURES

ensure_signals_registered()


@pytest.mark.parametrize(
    "fixture",
    [ALL_FIXTURES[0]],
    ids=[ALL_FIXTURES[0].name],
)
def test_signal_crash_surfaces_warning(tmp_path: Path, fixture) -> None:
    """A crashing signal must produce a RuntimeWarning and a matching AnalyzerWarning."""
    boom = RuntimeError("boom from broken signal")

    # create_signals is imported directly into precision.py, so we patch it there.
    import drift.precision as precision_mod

    original_create = precision_mod.create_signals

    def patched_create(ctx):
        real_signals = original_create(ctx)
        broken = MagicMock()
        broken.signal_type = "BROKEN_SIGNAL_TEST"
        broken.analyze.side_effect = boom
        return [broken] + real_signals

    with patch.object(precision_mod, "create_signals", side_effect=patched_create):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            findings, analyzer_warnings = run_fixture(fixture, tmp_path)

    runtime_warnings = [w for w in caught if issubclass(w.category, RuntimeWarning)]
    assert runtime_warnings, "Expected a RuntimeWarning for the crashing signal"
    assert any("BROKEN_SIGNAL_TEST" in str(w.message) for w in runtime_warnings)
    assert any("boom from broken signal" in str(w.message) for w in runtime_warnings)

    signal_warning_msgs = [w.message for w in analyzer_warnings]
    assert any(
        "BROKEN_SIGNAL_TEST" in m and "boom from broken signal" in m
        for m in signal_warning_msgs
    ), "Expected an AnalyzerWarning entry for the crashing signal"
