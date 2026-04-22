"""Arch-Analyzer: transitive Modul-Invalidierung via ArchGraph.

Nutzt den bereits persistierten ``arch_graph.json``, um Konsumenten geänderter
Module zu ermitteln. Wenn kein ArchGraph vorliegt (z. B. nach frischem Clone),
liefert der Analyzer einen leeren Impact-Set und dokumentiert das als
Degradation.
"""

from __future__ import annotations

import logging
from pathlib import Path

from drift.blast_radius._models import BlastImpact, BlastImpactKind, BlastSeverity

_log = logging.getLogger("drift.blast_radius.arch")


def _load_arch_graph(repo_path: Path) -> object | None:
    """Versuche, den ArchGraph zu laden — tolerant gegenüber Fehlern."""
    try:
        from drift.arch_graph import ArchGraphStore
    except ImportError:  # pragma: no cover — drift.arch_graph ist Kernmodul
        _log.debug("drift.arch_graph nicht importierbar.")
        return None
    try:
        store = ArchGraphStore(repo_path)
        return store.load()
    except Exception as exc:  # noqa: BLE001 — defensiv, Analyzer darf nicht crashen
        _log.debug("ArchGraph konnte nicht geladen werden: %s", exc)
        return None


def _module_for_file(graph: object, file_path: str) -> str | None:
    """Finde das Modul mit dem längsten Pfad-Prefix, das ``file_path`` enthält."""
    modules = getattr(graph, "modules", None)
    if not modules:
        return None
    best: str | None = None
    best_len = -1
    for module in modules:
        module_path = getattr(module, "path", "") or ""
        if not module_path:
            continue
        prefix = module_path if module_path.endswith("/") else module_path + "/"
        if (
            (file_path == module_path or file_path.startswith(prefix))
            and len(module_path) > best_len
        ):
            best_len = len(module_path)
            best = module_path
    return best


def _neighbors(graph: object, module_path: str) -> list[str]:
    """Konsumenten + Abhängigkeits-Ziele des Moduls."""
    deps = getattr(graph, "dependencies", None) or []
    result: set[str] = set()
    for dep in deps:
        from_m = getattr(dep, "from_module", None)
        to_m = getattr(dep, "to_module", None)
        if from_m == module_path and to_m:
            result.add(to_m)
        elif to_m == module_path and from_m:
            result.add(from_m)
    return sorted(result)


def analyze_arch_impacts(
    repo_path: Path,
    changed_files: tuple[str, ...],
) -> tuple[list[BlastImpact], list[str]]:
    """Ermittle transitive Modul-Invalidierungen.

    Returns
    -------
    (impacts, degradation_notes)
        ``degradation_notes`` enthält Strings, wenn z. B. kein ArchGraph
        vorliegt.
    """
    if not changed_files:
        return [], []

    graph = _load_arch_graph(repo_path)
    if graph is None:
        return [], [
            "ArchGraph nicht geladen — Modul-Dependency-Analyse übersprungen."
        ]

    impacts: list[BlastImpact] = []
    seen_modules: set[str] = set()
    for file_path in changed_files:
        module = _module_for_file(graph, file_path)
        if not module or module in seen_modules:
            continue
        seen_modules.add(module)
        consumers = _neighbors(graph, module)
        for consumer in consumers:
            impacts.append(
                BlastImpact(
                    kind=BlastImpactKind.ARCH_DEPENDENCY,
                    target_id=consumer,
                    target_path=consumer,
                    severity=BlastSeverity.MEDIUM,
                    reason=(
                        f"Modul {consumer!r} hängt von geändertem Modul "
                        f"{module!r} ab und muss re-validiert werden."
                    ),
                    scope_match=module,
                    matched_files=tuple(
                        f for f in changed_files if _module_for_file(graph, f) == module
                    ),
                    requires_maintainer_ack=False,
                )
            )
    # Deduplizieren (gleiche target_id kann aus mehreren Modulen kommen)
    unique: dict[str, BlastImpact] = {}
    for impact in impacts:
        key = f"{impact.kind.value}:{impact.target_id}"
        if key not in unique:
            unique[key] = impact
    return list(unique.values()), []
