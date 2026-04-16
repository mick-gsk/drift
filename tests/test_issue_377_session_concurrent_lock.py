"""Regression tests for per-session async lock protecting concurrent state mutations (#377).

Verifies that:
1. DriftSession.get_async_lock() returns a consistent asyncio.Lock.
2. session_call_lock() serialises concurrent writes to shared session fields.
3. Concurrent drift_scan-style state updates do not produce interleaved phase
   transitions or lost score writes.
"""

from __future__ import annotations

import asyncio

# ---------------------------------------------------------------------------
# 1. DriftSession.get_async_lock — lock identity and type
# ---------------------------------------------------------------------------


class TestGetAsyncLock:
    """DriftSession.get_async_lock returns a stable asyncio.Lock."""

    def _make_session(self) -> object:
        from drift.session import DriftSession

        return DriftSession(session_id="test-sid", repo_path=".")

    def test_returns_asyncio_lock(self) -> None:
        session = self._make_session()
        lock = session.get_async_lock()
        assert isinstance(lock, asyncio.Lock), (
            "get_async_lock() must return an asyncio.Lock instance (#377)"
        )

    def test_returns_same_instance_on_repeated_calls(self) -> None:
        session = self._make_session()
        lock_a = session.get_async_lock()
        lock_b = session.get_async_lock()
        assert lock_a is lock_b, (
            "get_async_lock() must return the same Lock object on every call (#377)"
        )

    def test_different_sessions_have_different_locks(self) -> None:
        from drift.session import DriftSession

        s1 = DriftSession(session_id="sid-1", repo_path=".")
        s2 = DriftSession(session_id="sid-2", repo_path=".")
        assert s1.get_async_lock() is not s2.get_async_lock(), (
            "Each DriftSession must own a distinct asyncio.Lock (#377)"
        )


# ---------------------------------------------------------------------------
# 2. session_call_lock — context manager behaviour
# ---------------------------------------------------------------------------


class TestSessionCallLock:
    """session_call_lock acquires the per-session lock and serialises calls."""

    def test_noop_when_session_is_none(self) -> None:
        """session_call_lock must be a no-op when session=None."""
        from drift.mcp_orchestration import session_call_lock

        async def _run() -> str:
            async with session_call_lock(None):
                return "ok"

        assert asyncio.run(_run()) == "ok"

    def test_acquires_lock(self) -> None:
        """session_call_lock must hold the lock while the body executes."""
        from drift.mcp_orchestration import session_call_lock
        from drift.session import DriftSession

        session = DriftSession(session_id="lock-test", repo_path=".")
        lock_held_during_body: list[bool] = []

        async def _run() -> None:
            async with session_call_lock(session):
                lock_held_during_body.append(session.get_async_lock().locked())

        asyncio.run(_run())
        assert lock_held_during_body == [True], (
            "session_call_lock must hold the lock while its body executes (#377)"
        )

    def test_lock_released_after_context_exit(self) -> None:
        """session_call_lock must release the lock on normal exit."""
        from drift.mcp_orchestration import session_call_lock
        from drift.session import DriftSession

        session = DriftSession(session_id="release-test", repo_path=".")

        async def _run() -> None:
            async with session_call_lock(session):
                pass
            assert not session.get_async_lock().locked(), (
                "Lock must be released after session_call_lock exits (#377)"
            )

        asyncio.run(_run())

    def test_lock_released_on_exception(self) -> None:
        """session_call_lock must release the lock even when the body raises."""
        from drift.mcp_orchestration import session_call_lock
        from drift.session import DriftSession

        session = DriftSession(session_id="exc-test", repo_path=".")

        async def _run() -> None:
            try:
                async with session_call_lock(session):
                    raise ValueError("test error")
            except ValueError:
                pass
            assert not session.get_async_lock().locked(), (
                "Lock must be released after session_call_lock exits on exception (#377)"
            )

        asyncio.run(_run())


# ---------------------------------------------------------------------------
# 3. Concurrent state mutation serialisation
# ---------------------------------------------------------------------------


class TestConcurrentStateMutations:
    """Concurrent tool calls on the same session must not interleave state writes."""

    def test_last_scan_score_not_lost_under_concurrency(self) -> None:
        """Two concurrent score-write coroutines must not produce a lost update."""
        from drift.mcp_orchestration import session_call_lock
        from drift.session import DriftSession

        session = DriftSession(session_id="concurrent-score", repo_path=".")
        writes: list[float] = []

        async def _write_score(score: float) -> None:
            async with session_call_lock(session):
                # Simulate async API work completing:
                await asyncio.sleep(0)
                session.last_scan_score = score
                writes.append(score)

        async def _run() -> None:
            await asyncio.gather(
                _write_score(5.0),
                _write_score(3.0),
            )

        asyncio.run(_run())

        # Both writes must have completed, and the final value must be one of them.
        assert len(writes) == 2, "Both concurrent writes must complete (#377)"
        assert session.last_scan_score in {5.0, 3.0}, (
            "final last_scan_score must be one of the written values (#377)"
        )

    def test_phase_transition_not_duplicated_under_concurrency(self) -> None:
        """Two concurrent scan updates must not advance phase twice."""
        from drift.mcp_orchestration import _update_session_from_scan, session_call_lock
        from drift.session import DriftSession

        session = DriftSession(session_id="concurrent-phase", repo_path=".")
        scan_result = {"drift_score": 4.0, "top_signals": [], "finding_count": 2}

        async def _do_scan_update() -> None:
            async with session_call_lock(session):
                await asyncio.sleep(0)  # yield to allow concurrent entry
                _update_session_from_scan(session, scan_result)

        async def _run() -> None:
            await asyncio.gather(_do_scan_update(), _do_scan_update())

        asyncio.run(_run())

        # Phase must be exactly "scan" — not skipped to a later stage.
        assert session.phase == "scan", (
            f"Concurrent scan updates must not skip or corrupt phase: got {session.phase!r} (#377)"
        )

    def test_completed_task_ids_no_duplicates_under_concurrency(self) -> None:
        """Concurrent completed_task_ids extensions must not produce duplicates."""
        from drift.mcp_orchestration import session_call_lock
        from drift.session import DriftSession

        session = DriftSession(session_id="concurrent-tasks", repo_path=".")
        session.completed_task_ids = []

        async def _mark_complete(task_id: str) -> None:
            async with session_call_lock(session):
                await asyncio.sleep(0)
                existing = list(session.completed_task_ids)
                if task_id not in existing:
                    existing.append(task_id)
                session.completed_task_ids = existing

        async def _run() -> None:
            # Both coroutines try to add the same task_id
            await asyncio.gather(
                _mark_complete("task-1"),
                _mark_complete("task-1"),
            )

        asyncio.run(_run())

        assert session.completed_task_ids.count("task-1") == 1, (
            "Concurrent task completions must not produce duplicate IDs (#377)"
        )

    def test_second_call_blocked_while_first_holds_lock(self) -> None:
        """A second session_call_lock on the same session must wait for the first."""
        from drift.mcp_orchestration import session_call_lock
        from drift.session import DriftSession

        session = DriftSession(session_id="serialisation-test", repo_path=".")
        execution_order: list[str] = []

        async def _first() -> None:
            async with session_call_lock(session):
                execution_order.append("first:enter")
                await asyncio.sleep(0.01)  # hold lock briefly
                execution_order.append("first:exit")

        async def _second() -> None:
            # Give first a head start so it acquires the lock first.
            await asyncio.sleep(0)
            async with session_call_lock(session):
                execution_order.append("second:enter")

        async def _run() -> None:
            await asyncio.gather(_first(), _second())

        asyncio.run(_run())

        # second must not enter until first has exited.
        assert execution_order == ["first:enter", "first:exit", "second:enter"], (
            f"session_call_lock must serialise: got {execution_order} (#377)"
        )


# ---------------------------------------------------------------------------
# 4. session_call_lock export from mcp_orchestration
# ---------------------------------------------------------------------------


class TestSessionCallLockIsExported:
    """session_call_lock must be importable from drift.mcp_orchestration."""

    def test_importable(self) -> None:
        from drift.mcp_orchestration import session_call_lock  # noqa: F401

        assert callable(session_call_lock), (
            "session_call_lock must be exported from drift.mcp_orchestration (#377)"
        )
