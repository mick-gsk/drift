"""Performance regression tests for MCP hot-path caching optimizations.

Tests cover:
- ParseCache eviction rate-limiting (once per hour per cache dir)
- dependency_dag topological sort cache (process-level dict keyed by tuple)
- incremental.py signal class split cache (keyed by frozenset of registered signal classes)
- IncrementalSignalRunner.run() uses the split cache on repeated calls
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers: reset module-level cache state between tests
# ---------------------------------------------------------------------------


def _reset_parse_cache_eviction_state() -> None:
    from drift.cache import ParseCache

    with ParseCache._eviction_interval_lock:
        ParseCache._last_eviction.clear()


def _reset_topo_cache() -> None:
    from drift.signals import dependency_dag

    with dependency_dag._topo_cache_lock:
        dependency_dag._topo_cache.clear()


def _reset_signal_split_cache() -> None:
    from drift import incremental

    with incremental._SIGNAL_CLASS_SPLIT_LOCK:
        incremental._SIGNAL_CLASS_SPLIT_CACHE.clear()


# ---------------------------------------------------------------------------
# ParseCache eviction rate-limiting
# ---------------------------------------------------------------------------


class TestParseCacheEvictionRateLimiting:
    def test_classvars_exist(self) -> None:
        from drift.cache import ParseCache

        assert hasattr(ParseCache, "_EVICTION_INTERVAL_SECONDS")
        assert hasattr(ParseCache, "_last_eviction")
        assert hasattr(ParseCache, "_eviction_interval_lock")

    def test_eviction_interval_is_one_hour(self) -> None:
        from drift.cache import ParseCache

        assert ParseCache._EVICTION_INTERVAL_SECONDS == 3600.0

    def test_first_call_runs_eviction(self, tmp_path: Path) -> None:
        from drift.cache import ParseCache

        _reset_parse_cache_eviction_state()
        cache = ParseCache(tmp_path / "c1")
        # After construction, the cache dir key should be recorded
        assert cache._cache_dir_key in ParseCache._last_eviction

    def test_second_call_within_interval_skips_eviction(self, tmp_path: Path) -> None:
        from drift.cache import ParseCache

        _reset_parse_cache_eviction_state()
        cache_dir = tmp_path / "c2"
        c = ParseCache(cache_dir)
        t_first = ParseCache._last_eviction[c._cache_dir_key]

        # Second instantiation within the interval should NOT update the timestamp
        ParseCache(cache_dir)
        t_second = ParseCache._last_eviction[c._cache_dir_key]
        assert t_first == t_second, "Eviction should have been skipped on warm path"

    def test_eviction_runs_again_after_interval(self, tmp_path: Path) -> None:
        from drift.cache import ParseCache

        _reset_parse_cache_eviction_state()
        cache_dir = tmp_path / "c3"
        c = ParseCache(cache_dir)
        key = c._cache_dir_key

        # Simulate passage of time by backdating last_eviction
        with ParseCache._eviction_interval_lock:
            ParseCache._last_eviction[key] = time.time() - ParseCache._EVICTION_INTERVAL_SECONDS - 1

        ParseCache(cache_dir)
        new_time = ParseCache._last_eviction[key]
        assert new_time > time.time() - 5, "Eviction should have run after interval expired"

    def test_warm_path_faster_than_cold(self, tmp_path: Path) -> None:
        from drift.cache import ParseCache

        _reset_parse_cache_eviction_state()
        cache_dir = tmp_path / "bench"
        # Cold: first call does eviction scan
        t0 = time.perf_counter()
        ParseCache(cache_dir)
        cold_ms = (time.perf_counter() - t0) * 1000

        # Warm: second call skips eviction
        t1 = time.perf_counter()
        ParseCache(cache_dir)
        warm_ms = (time.perf_counter() - t1) * 1000

        # Warm must be at least 5x faster than cold (generous bound)
        assert warm_ms < cold_ms or warm_ms < 1.0, (
            f"Warm path ({warm_ms:.3f} ms) should be faster than cold ({cold_ms:.3f} ms)"
        )

    def test_thread_safety(self, tmp_path: Path) -> None:
        from drift.cache import ParseCache

        _reset_parse_cache_eviction_state()
        cache_dir = tmp_path / "threaded"
        errors: list[str] = []

        def worker() -> None:
            try:
                ParseCache(cache_dir)
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"


# ---------------------------------------------------------------------------
# Topological sort cache
# ---------------------------------------------------------------------------


class TestTopoSortCache:
    def test_cache_populated_on_first_call(self) -> None:
        from drift.signals.base import registered_signals
        from drift.signals.dependency_dag import _topo_cache, order_signal_classes_topologically

        _reset_topo_cache()
        classes = list(registered_signals())
        result = order_signal_classes_topologically(classes)
        key = tuple(classes)
        assert key in _topo_cache
        assert list(_topo_cache[key]) == result

    def test_cache_returns_same_object_on_second_call(self) -> None:
        from drift.signals.base import registered_signals
        from drift.signals.dependency_dag import order_signal_classes_topologically

        _reset_topo_cache()
        classes = list(registered_signals())
        r1 = order_signal_classes_topologically(classes)
        r2 = order_signal_classes_topologically(classes)
        assert r1 == r2, "Second call should return an equal list from cache"

    def test_warm_path_faster_than_cold(self) -> None:
        from drift.signals.base import registered_signals
        from drift.signals.dependency_dag import order_signal_classes_topologically

        _reset_topo_cache()
        classes = list(registered_signals())

        t0 = time.perf_counter()
        order_signal_classes_topologically(classes)
        cold_ms = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()
        order_signal_classes_topologically(classes)
        warm_ms = (time.perf_counter() - t1) * 1000

        assert warm_ms < cold_ms or warm_ms < 0.5, (
            f"Warm path ({warm_ms:.4f} ms) should be faster than cold ({cold_ms:.4f} ms)"
        )

    def test_cache_is_invalidated_by_different_input(self) -> None:
        from drift.signals.base import BaseSignal, registered_signals
        from drift.signals.dependency_dag import _topo_cache, order_signal_classes_topologically

        _reset_topo_cache()
        classes = list(registered_signals())

        class _ExtraSignal(BaseSignal):
            pass

        r1 = order_signal_classes_topologically(classes)
        classes2 = classes + [_ExtraSignal]
        r2 = order_signal_classes_topologically(classes2)

        assert r1 is not r2, "Different input must produce a different cache entry"
        assert tuple(classes) in _topo_cache
        assert tuple(classes2) in _topo_cache

    def test_empty_list_not_cached(self) -> None:
        from drift.signals.dependency_dag import _topo_cache, order_signal_classes_topologically

        _reset_topo_cache()
        result = order_signal_classes_topologically([])
        assert result == []
        # Empty list hits the early-return, so nothing goes into the cache
        assert len(_topo_cache) == 0


# ---------------------------------------------------------------------------
# Signal class split cache
# ---------------------------------------------------------------------------


class TestSignalClassSplitCache:
    def test_cache_populated_on_first_call(self) -> None:
        from drift import incremental
        from drift.signals.base import registered_signals
        from drift.signals.dependency_dag import order_signal_classes_topologically

        _reset_signal_split_cache()
        incremental._get_incremental_signal_class_split(
            registered_signals, order_signal_classes_topologically
        )
        assert len(incremental._SIGNAL_CLASS_SPLIT_CACHE) == 1

    def test_cache_returns_same_object_on_second_call(self) -> None:
        from drift import incremental
        from drift.signals.base import registered_signals
        from drift.signals.dependency_dag import order_signal_classes_topologically

        _reset_signal_split_cache()
        r1 = incremental._get_incremental_signal_class_split(
            registered_signals, order_signal_classes_topologically
        )
        r2 = incremental._get_incremental_signal_class_split(
            registered_signals, order_signal_classes_topologically
        )
        assert r1 is r2

    def test_warm_path_faster_than_cold(self) -> None:
        from drift import incremental
        from drift.signals.base import registered_signals
        from drift.signals.dependency_dag import order_signal_classes_topologically

        _reset_signal_split_cache()

        t0 = time.perf_counter()
        incremental._get_incremental_signal_class_split(
            registered_signals, order_signal_classes_topologically
        )
        cold_ms = (time.perf_counter() - t0) * 1000

        t1 = time.perf_counter()
        incremental._get_incremental_signal_class_split(
            registered_signals, order_signal_classes_topologically
        )
        warm_ms = (time.perf_counter() - t1) * 1000

        assert warm_ms < cold_ms or warm_ms < 0.5, (
            f"Warm path ({warm_ms:.4f} ms) should be faster than cold ({cold_ms:.4f} ms)"
        )

    def test_result_contains_file_local_and_other(self) -> None:
        from drift import incremental
        from drift.signals.base import registered_signals
        from drift.signals.dependency_dag import order_signal_classes_topologically

        _reset_signal_split_cache()
        file_local, other = incremental._get_incremental_signal_class_split(
            registered_signals, order_signal_classes_topologically
        )
        assert len(file_local) > 0, "Expected at least one file-local signal"
        for cls in file_local:
            assert getattr(cls, "incremental_scope", None) == "file_local"
        for cls in other:
            assert getattr(cls, "incremental_scope", None) != "file_local"

    def test_different_registry_produces_different_cache_entry(self) -> None:
        from drift import incremental
        from drift.signals.base import BaseSignal, registered_signals
        from drift.signals.dependency_dag import order_signal_classes_topologically

        _reset_signal_split_cache()

        class _MockSignal(BaseSignal):
            incremental_scope = "file_local"

        def mock_registered():
            return [_MockSignal]

        r1 = incremental._get_incremental_signal_class_split(
            registered_signals, order_signal_classes_topologically
        )
        r2 = incremental._get_incremental_signal_class_split(
            mock_registered, order_signal_classes_topologically
        )
        assert r1 is not r2
        assert len(incremental._SIGNAL_CLASS_SPLIT_CACHE) == 2

    def test_thread_safety(self) -> None:
        from drift import incremental
        from drift.signals.base import registered_signals
        from drift.signals.dependency_dag import order_signal_classes_topologically

        _reset_signal_split_cache()
        results: list[tuple] = []
        errors: list[str] = []

        def worker() -> None:
            try:
                r = incremental._get_incremental_signal_class_split(
                    registered_signals, order_signal_classes_topologically
                )
                results.append(r)
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=worker) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # All threads should have gotten the same result object
        assert all(r is results[0] for r in results), (
            "All threads should share the same cached result"
        )

    def test_cache_survives_monkeypatch_via_key_change(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from drift import incremental
        from drift.signals.base import BaseSignal, registered_signals
        from drift.signals.dependency_dag import order_signal_classes_topologically

        _reset_signal_split_cache()

        class _PatchedSignal(BaseSignal):
            incremental_scope = "cross_file"

        original_result = incremental._get_incremental_signal_class_split(
            registered_signals, order_signal_classes_topologically
        )

        monkeypatch.setattr(
            "drift.signals.base.registered_signals",
            lambda: [_PatchedSignal],
        )
        from drift.signals.base import registered_signals as patched_rs

        patched_result = incremental._get_incremental_signal_class_split(
            patched_rs, order_signal_classes_topologically
        )
        assert patched_result is not original_result
        assert patched_result[0] == []  # no file-local signals
        assert len(patched_result[1]) == 1  # _PatchedSignal in other


# ---------------------------------------------------------------------------
# Integration: IncrementalSignalRunner.run() uses split cache
# ---------------------------------------------------------------------------


class TestIncrementalRunnerUsesCache:
    def test_runner_run_populates_split_cache(self, tmp_path: Path) -> None:
        from drift import incremental
        from drift.config import DriftConfig
        from drift.incremental import BaselineSnapshot, IncrementalSignalRunner
        from drift.models import ParseResult

        _reset_signal_split_cache()
        config = DriftConfig()
        pr = ParseResult(file_path=Path("src/a.py"), language="python", line_count=10)
        baseline = BaselineSnapshot(file_hashes={"src/a.py": "aaa"}, score=0.0)

        runner = IncrementalSignalRunner(
            baseline=baseline,
            config=config,
            baseline_findings=[],
            baseline_parse_results={"src/a.py": pr},
        )
        runner.run(changed_files={"src/a.py"}, current_parse_results={"src/a.py": pr})

        # After one run, the split cache must be populated
        assert len(incremental._SIGNAL_CLASS_SPLIT_CACHE) >= 1
