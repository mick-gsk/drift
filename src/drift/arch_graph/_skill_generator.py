"""Skill-briefing generator — structured data for agent-driven SKILL.md creation.

Analyses the ``ArchGraph`` to produce per-module ``SkillBriefing`` objects.
Each briefing contains the structured data an AI agent needs to write a
``SKILL.md`` file for that module.

This module produces *data*, not prose — the API layer adds the
``agent_instruction`` that tells the agent what to do with it.
"""

from __future__ import annotations

from collections import defaultdict

from drift.arch_graph._decisions import format_decision_constraints, match_decisions
from drift.arch_graph._models import (
    ArchGraph,
    SkillBriefing,
)

_DEFAULT_MIN_OCCURRENCES = 4
_DEFAULT_MIN_CONFIDENCE = 0.6


def generate_skill_briefings(
    graph: ArchGraph,
    *,
    min_occurrences: int = _DEFAULT_MIN_OCCURRENCES,
    min_confidence: float = _DEFAULT_MIN_CONFIDENCE,
) -> list[SkillBriefing]:
    """Generate skill briefings for modules with recurring problems.

    Parameters
    ----------
    graph:
        A populated ``ArchGraph`` with modules, hotspots, etc.
    min_occurrences:
        Minimum total signal occurrences across a module's hotspots
        to qualify for a briefing.
    min_confidence:
        Minimum confidence score to include the briefing.

    Returns
    -------
    list[SkillBriefing]
        One briefing per qualifying module, sorted by confidence descending.
    """
    if not graph.hotspots:
        return []

    # Step 1: aggregate hotspot signals by module
    module_data: dict[str, _ModuleAgg] = defaultdict(_ModuleAgg)

    for hs in graph.hotspots:
        module_path = _resolve_module_path(graph, hs.path)
        agg = module_data[module_path]
        agg.files.add(hs.path)
        agg.trends.add(hs.trend)
        for signal_id, count in hs.recurring_signals.items():
            agg.signals[signal_id] += count
            agg.total += count

    # Step 2: build briefings for qualifying modules
    briefings: list[SkillBriefing] = []

    for module_path, agg in sorted(module_data.items()):
        # Check minimum occurrences (sum of all signals in module)
        qualifying_signals = {
            sid: cnt for sid, cnt in agg.signals.items() if cnt >= min_occurrences
        }
        if not qualifying_signals:
            continue

        # Compute confidence
        is_degrading = "degrading" in agg.trends
        confidence = _compute_confidence(agg.total, min_occurrences, is_degrading)
        if confidence < min_confidence:
            continue

        # Gather module metadata
        mod = graph.get_module(module_path)
        layer = mod.layer if mod else None
        neighbors = graph.neighbors(module_path)
        abstractions = [a.symbol for a in graph.abstractions_in(module_path)]

        # Gather decision constraints
        constraints: list[dict[str, str]] = []
        if graph.decisions:
            # Match against module_path and as a child path (for glob scopes)
            matching = match_decisions(graph.decisions, module_path)
            if not matching:
                matching = match_decisions(graph.decisions, module_path + "/_.py")
            if matching:
                constraints = format_decision_constraints(matching)

        briefings.append(
            SkillBriefing(
                name=_to_kebab(module_path),
                module_path=module_path,
                trigger_signals=sorted(qualifying_signals.keys()),
                constraints=constraints,
                hotspot_files=sorted(agg.files),
                layer=layer,
                neighbors=neighbors,
                abstractions=abstractions,
                confidence=confidence,
            )
        )

    # Sort by confidence descending (most urgent first)
    briefings.sort(key=lambda b: b.confidence, reverse=True)
    return briefings


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _ModuleAgg:
    """Mutable accumulator for per-module hotspot aggregation."""

    __slots__ = ("signals", "files", "trends", "total")

    def __init__(self) -> None:
        self.signals: dict[str, int] = defaultdict(int)
        self.files: set[str] = set()
        self.trends: set[str] = set()
        self.total: int = 0


def _resolve_module_path(graph: ArchGraph, file_path: str) -> str:
    """Map a file path to its enclosing module in the graph."""
    normalised = file_path.replace("\\", "/")
    best_match = ""
    for m in graph.modules:
        m_norm = m.path.replace("\\", "/")
        if (normalised.startswith(m_norm + "/") or normalised == m_norm) and len(m_norm) > len(
            best_match
        ):
            best_match = m_norm
    if not best_match:
        parts = normalised.rsplit("/", 1)
        best_match = parts[0] if len(parts) > 1 else normalised
    return best_match


def _compute_confidence(
    total: int,
    min_occurrences: int,
    is_degrading: bool,
) -> float:
    """Compute a confidence score in [0.5, 1.0]."""
    ratio = min(total / max(min_occurrences * 3, 1), 1.0)
    base = 0.5 + ratio * 0.35
    if is_degrading:
        base = min(base + 0.1, 1.0)
    return round(base, 2)


def _to_kebab(module_path: str) -> str:
    """Convert a module path to a kebab-case skill name."""
    return "guard-" + module_path.replace("/", "-").replace("\\", "-").replace("_", "-").lower()
