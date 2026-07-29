"""Executor factory with a synchronous fallback for thread-less platforms.

Pyodide/Emscripten (e.g. the browser playground) cannot start OS threads:
``ThreadPoolExecutor`` raises ``RuntimeError: can't start new thread`` the
moment a worker is spawned. :func:`make_executor` returns a drop-in
synchronous executor on such platforms so the pipeline degrades to
sequential execution instead of crashing.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from concurrent.futures import Executor, Future, ThreadPoolExecutor
from typing import Any, TypeVar

_T = TypeVar("_T")


def _threads_available() -> bool:
    """Whether this platform can start OS threads."""
    return sys.platform != "emscripten"


class InlineExecutor(Executor):
    """Synchronous ``Executor``: runs each task inline on ``submit``.

    ``map``, ``shutdown``, and context-manager behaviour come from the
    :class:`concurrent.futures.Executor` base class, which routes through
    ``submit`` — so this is a drop-in replacement wherever a
    ``ThreadPoolExecutor`` is used with ``submit``/``map``/``as_completed``.
    """

    def submit(  # type: ignore[override]
        self, fn: Callable[..., _T], /, *args: Any, **kwargs: Any
    ) -> Future[_T]:
        future: Future[_T] = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except BaseException as exc:  # noqa: BLE001 — mirror thread behaviour
            future.set_exception(exc)
        return future


def make_executor(max_workers: int) -> Executor:
    """Return a ``ThreadPoolExecutor``, or an :class:`InlineExecutor` where
    threads are unavailable (Pyodide/WASM)."""
    if not _threads_available():
        return InlineExecutor()
    return ThreadPoolExecutor(max_workers=max_workers)
