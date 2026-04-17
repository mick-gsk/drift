"""Synthesize endpoint — cluster, generate, and triage skill drafts."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

from drift.api_helpers import _base_response
from drift.calibration.feedback import load_feedback
from drift.calibration.history import load_snapshots
from drift.synthesizer._cluster import build_finding_clusters
from drift.synthesizer._draft_generator import generate_skill_drafts
from drift.synthesizer._triage import triage_skill_drafts

log = logging.getLogger(__name__)


def synthesize(
    repo: str = ".",
    *,
    kinds: str = "all",
    min_recurrence: int = 3,
    min_recurrence_rate: float = 0.5,
    max_skills: int = 25,
    merge_threshold: float = 0.4,
    discard_confidence: float = 0.55,
) -> dict[str, Any]:
    """Run the full synthesizer pipeline: cluster → draft → triage.

    Parameters
    ----------
    repo:
        Path to the repository root.
    kinds:
        Which skill types to generate: 'guard', 'repair', or 'all'.
    min_recurrence:
        Minimum finding recurrences for clustering.
    min_recurrence_rate:
        Minimum recurrence rate for clustering.
    max_skills:
        Sprawl guard limit for triage.
    merge_threshold:
        Overlap threshold for merge decisions.
    discard_confidence:
        Confidence below which drafts are discarded.

    Returns
    -------
    dict
        API response with clusters, drafts, and triage decisions.
    """
    repo_path = Path(repo).resolve()
    cache_dir = repo_path / ".drift-cache"
    history_dir = cache_dir / "history"
    feedback_path = cache_dir / "feedback.jsonl"

    # Load scan history
    snapshots = load_snapshots(history_dir) if history_dir.is_dir() else []
    if not snapshots:
        return _base_response(
            endpoint="synthesize",
            status="insufficient_data",
            message="Keine Scan-Snapshots gefunden. Mindestens 3 Scans noetig.",
            clusters=[],
            drafts=[],
            decisions=[],
            agent_instruction="Fuehre zuerst mehrere `drift scan` Laeufe durch.",
        )

    # Load feedback
    feedback_events = load_feedback(feedback_path) if feedback_path.is_file() else []

    # Load ArchGraph if available
    graph = _load_arch_graph(cache_dir)

    # Extract known module paths from ArchGraph
    known_modules = (
        [m.path for m in graph.modules] if graph and graph.modules else None
    )

    # Step 1: Cluster
    clusters = build_finding_clusters(
        snapshots,
        feedback_events or None,
        known_modules=known_modules,
        min_recurrence=min_recurrence,
        min_recurrence_rate=min_recurrence_rate,
    )

    if not clusters:
        return _base_response(
            endpoint="synthesize",
            status="no_clusters",
            message="Keine wiederkehrenden Befund-Cluster gefunden.",
            clusters=[],
            drafts=[],
            decisions=[],
            agent_instruction="Schwellenwerte pruefen oder mehr Scans sammeln.",
        )

    # Step 2: Generate drafts
    _valid_kinds = ("guard", "repair", "all")
    _kinds: Literal["guard", "repair", "all"] = kinds if kinds in _valid_kinds else "all"  # type: ignore[assignment]
    drafts = generate_skill_drafts(clusters, graph, kinds=_kinds)

    # Step 3: Triage
    decisions = triage_skill_drafts(
        drafts,
        repo_root=repo_path,
        max_skills=max_skills,
        merge_threshold=merge_threshold,
        discard_confidence=discard_confidence,
    )

    # Summary counts
    action_counts = {"new": 0, "merge": 0, "discard": 0}
    for d in decisions:
        action_counts[d.action] = action_counts.get(d.action, 0) + 1

    return _base_response(
        endpoint="synthesize",
        status="ok",
        cluster_count=len(clusters),
        draft_count=len(drafts),
        decisions_summary=action_counts,
        clusters=[c.to_dict() for c in clusters],
        drafts=[d.to_dict() for d in drafts],
        decisions=[d.to_dict() for d in decisions],
        agent_instruction=(
            f"{action_counts['new']} neue Skills, "
            f"{action_counts['merge']} Merge-Vorschlaege, "
            f"{action_counts['discard']} verworfen. "
            "Prüfe die Vorschlaege und entscheide manuell."
        ),
    )


def _load_arch_graph(cache_dir: Path) -> Any:
    """Load ArchGraph from cache, returns None if unavailable."""
    graph_path = cache_dir / "arch_graph.json"
    if not graph_path.is_file():
        return None
    try:
        from drift.arch_graph._models import ArchGraph  # type: ignore[import-not-found]

        raw = json.loads(graph_path.read_text(encoding="utf-8"))
        return ArchGraph.from_dict(raw)
    except (ImportError, Exception):
        log.debug("Could not load ArchGraph from cache", exc_info=True)
        return None
