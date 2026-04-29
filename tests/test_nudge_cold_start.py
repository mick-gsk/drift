"""Tests for drift_nudge cold-start latency (Feature 05 / ADR-085).

Verifies that the first ``nudge()`` call (no in-memory baseline, no disk baseline)
completes in under 1 second on a minimal fixture repository.

Environment variable ``DRIFT_COLD_START_TOLERANCE`` can be set to a float multiplier
to relax the timing assertion in slow CI environments (default: 1.0, i.e. < 1.0 s).
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from drift.api import _baseline_store, nudge
from drift.incremental import BaselineManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COLD_START_LIMIT_S = float(os.environ.get("DRIFT_COLD_START_TOLERANCE", "1.0"))


def _stub_analysis(**kwargs: object) -> SimpleNamespace:
    return SimpleNamespace(
        findings=[],
        drift_score=0.1,
        severity=None,
        total_files=10,
        total_functions=30,
        ai_attributed_ratio=0.0,
        trend=None,
        analysis_duration_seconds=0.05,
        skipped_files=0,
        skipped_languages={},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNudgeColdStartLatency:
    """Verify first-call latency is under the cold-start budget."""

    @pytest.fixture(autouse=True)
    def _clean_state(self, tmp_path: Path) -> None:
        """Wipe in-memory baseline store and singleton before each test."""
        _baseline_store.clear()
        BaselineManager.reset_instance()
        yield
        _baseline_store.clear()
        BaselineManager.reset_instance()

    def test_cold_start_latency_under_limit(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """First nudge() call must complete within DRIFT_COLD_START_TOLERANCE seconds.

        The heavy work is mocked so this test only covers the dispatch overhead and
        the absence of the old redundant I/O loop in _create_baseline().
        """
        from drift.config import DriftConfig

        monkeypatch.setattr(
            DriftConfig,
            "load",
            staticmethod(lambda *a, **kw: DriftConfig()),
        )
        monkeypatch.setattr(
            "drift.analyzer.analyze_repo",
            lambda *a, **kw: _stub_analysis(),
        )
        monkeypatch.setattr(
            "drift.api._emit_api_telemetry",
            lambda **kw: None,
        )
        monkeypatch.setattr(
            "drift.signals.base.registered_signals",
            lambda: [],
        )

        start = time.monotonic()
        result = nudge(tmp_path, changed_files=[])
        elapsed = time.monotonic() - start

        assert elapsed < _COLD_START_LIMIT_S, (
            f"Cold-start nudge() took {elapsed:.3f}s, expected < {_COLD_START_LIMIT_S}s. "
            "This may indicate the redundant I/O loop in _create_baseline() was re-introduced. "
            "See ADR-085 and work_artifacts/feature_05_2026-04-21/profile_before.md."
        )
        assert result["baseline_created"] is True

    def test_file_hashes_populated_from_pipeline(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """When analyze_repo populates file_hashes_out, the baseline stores them.

        Verifies that the out-parameter wiring is correct: a fake analyze_repo that
        writes to file_hashes_out produces a baseline with those hashes.
        """
        from drift.config import DriftConfig

        expected_hashes = {"src/a.py": "abc123", "src/b.py": "def456"}

        def _fake_analyze(repo_path: Path, config=None, file_hashes_out=None, **kw):  # type: ignore[override]
            if file_hashes_out is not None:
                file_hashes_out.update(expected_hashes)
            return _stub_analysis()

        monkeypatch.setattr(
            DriftConfig,
            "load",
            staticmethod(lambda *a, **kw: DriftConfig()),
        )
        monkeypatch.setattr("drift.analyzer.analyze_repo", _fake_analyze)
        monkeypatch.setattr("drift.api._emit_api_telemetry", lambda **kw: None)
        monkeypatch.setattr("drift.signals.base.registered_signals", lambda: [])

        nudge(tmp_path, changed_files=[])

        mgr = BaselineManager.instance()
        stored = mgr.get(tmp_path, config=DriftConfig())
        assert stored is not None
        baseline, _findings, _parse_map = stored
        assert baseline.file_hashes == expected_hashes

    def test_parse_map_is_empty_on_cold_start(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """_create_baseline() must store an empty parse_map (same as disk warm-load path).

        IncrementalSignalRunner handles empty parse_map correctly; this test guards
        against accidentally re-introducing parse_map population on cold start.
        """
        from drift.config import DriftConfig

        monkeypatch.setattr(
            DriftConfig,
            "load",
            staticmethod(lambda *a, **kw: DriftConfig()),
        )
        monkeypatch.setattr(
            "drift.analyzer.analyze_repo",
            lambda *a, **kw: _stub_analysis(),
        )
        monkeypatch.setattr("drift.api._emit_api_telemetry", lambda **kw: None)
        monkeypatch.setattr("drift.signals.base.registered_signals", lambda: [])

        nudge(tmp_path, changed_files=[])

        mgr = BaselineManager.instance()
        stored = mgr.get(tmp_path, config=DriftConfig())
        assert stored is not None
        _baseline, _findings, parse_map = stored
        assert parse_map == {}, (
            "parse_map should be empty on cold-start baseline creation (ADR-085). "
            "Non-empty parse_map means the old redundant I/O loop was re-introduced."
        )
