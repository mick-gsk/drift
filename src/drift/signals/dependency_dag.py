"""Signal dependency DAG utilities for deterministic scheduling."""

from __future__ import annotations

import threading
from collections import defaultdict, deque

from drift.signals.base import BaseSignal

_topo_cache: dict[frozenset[type[BaseSignal]], list[type[BaseSignal]]] = {}
_topo_cache_lock = threading.Lock()


def order_signal_classes_topologically(
    classes: list[type[BaseSignal]],
) -> list[type[BaseSignal]]:
    """Return classes in dependency order while preserving stable fallback order.

    Signals may declare dependencies via ``depends_on_signals`` containing
    signal-type values. Unknown dependencies are ignored to keep legacy
    behavior unchanged.
    """
    if len(classes) <= 1:
        return classes

    cache_key = frozenset(classes)
    cached = _topo_cache.get(cache_key)
    if cached is not None:
        return cached

    by_signal_name: dict[str, type[BaseSignal]] = {}
    index_by_class: dict[type[BaseSignal], int] = {}
    for idx, cls in enumerate(classes):
        index_by_class[cls] = idx
        try:
            instance = cls()
            signal_name = str(instance.signal_type)
            by_signal_name[signal_name] = cls
        except Exception:
            continue

    adjacency: dict[type[BaseSignal], set[type[BaseSignal]]] = defaultdict(set)
    indegree: dict[type[BaseSignal], int] = {cls: 0 for cls in classes}

    for cls in classes:
        deps = getattr(cls, "depends_on_signals", ()) or ()
        for dep_name in deps:
            dep_cls = by_signal_name.get(str(dep_name))
            if dep_cls is None or dep_cls is cls:
                continue
            if cls in adjacency[dep_cls]:
                continue
            adjacency[dep_cls].add(cls)
            indegree[cls] += 1

    n = len(classes)
    queue = deque(
        sorted(
            [c for c, d in indegree.items() if d == 0],
            key=lambda c: index_by_class.get(c, n),
        )
    )
    ordered: list[type[BaseSignal]] = []

    while queue:
        cls = queue.popleft()
        ordered.append(cls)
        for nxt in sorted(
            adjacency.get(cls, ()),
            key=lambda c: index_by_class.get(c, n),
        ):
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)

    if len(ordered) != len(classes):
        # Cycle or unknown edge case: preserve previous deterministic order.
        return classes
    with _topo_cache_lock:
        _topo_cache[cache_key] = ordered
    return ordered
