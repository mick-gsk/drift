"""Tests for the thread-less executor fallback (Pyodide/WASM support)."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, as_completed

import pytest

from drift import executors
from drift.executors import InlineExecutor, make_executor


class TestInlineExecutor:
    def test_submit_returns_resolved_future(self) -> None:
        with InlineExecutor() as pool:
            future = pool.submit(lambda x: x * 2, 21)
        assert isinstance(future, Future)
        assert future.done()
        assert future.result() == 42

    def test_submit_captures_exception(self) -> None:
        def _boom() -> None:
            raise ValueError("boom")

        with InlineExecutor() as pool:
            future = pool.submit(_boom)
        assert future.done()
        with pytest.raises(ValueError, match="boom"):
            future.result()

    def test_map_preserves_order(self) -> None:
        with InlineExecutor() as pool:
            assert list(pool.map(str.upper, ["a", "b", "c"])) == ["A", "B", "C"]

    def test_as_completed_works_with_inline_futures(self) -> None:
        with InlineExecutor() as pool:
            futures = {pool.submit(lambda v=v: v): v for v in range(3)}
        results = {f.result() for f in as_completed(futures, timeout=1)}
        assert results == {0, 1, 2}


class TestMakeExecutor:
    def test_returns_thread_pool_when_threads_available(self) -> None:
        executor = make_executor(2)
        try:
            assert isinstance(executor, ThreadPoolExecutor)
        finally:
            executor.shutdown()

    def test_returns_inline_executor_on_emscripten(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(executors.sys, "platform", "emscripten")
        executor = make_executor(2)
        assert isinstance(executor, InlineExecutor)
        with executor as pool:
            assert pool.submit(sum, (1, 2)).result() == 3
