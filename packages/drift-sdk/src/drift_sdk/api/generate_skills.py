"""Generate Skills API — agent-prompt-based skill briefings.

Analyses the persisted ``ArchGraph`` and generates structured
``SkillBriefing`` objects for modules with recurring problems.
The ``agent_instruction`` tells the consuming AI agent how to
create ``SKILL.md`` files from the briefings.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from drift.arch_graph import ArchGraphStore
from drift.arch_graph._skill_generator import generate_skill_briefings
from drift.next_step_contract import _error_response, _next_step_contract
from drift.response_shaping import shape_for_profile
from drift.telemetry import timed_call

_log = logging.getLogger("drift")


def generate_skills(
    path: str | Path = ".",
    *,
    cache_dir: str | None = None,
    min_occurrences: int = 4,
    min_confidence: float = 0.6,
    response_profile: str | None = None,
) -> dict[str, Any]:
    """Generate skill briefings for modules with recurring drift patterns.

    Returns structured data and an ``agent_instruction`` that directs
    the consuming agent to create ``.github/skills/<name>/SKILL.md``
    files from the briefings.

    Parameters
    ----------
    path:
        Repository root path.
    cache_dir:
        Explicit cache directory.  Defaults to ``{repo}/.drift-cache``.
    min_occurrences:
        Minimum signal recurrence to trigger a briefing.
    min_confidence:
        Minimum confidence score to include a briefing.
    response_profile:
        Optional profile for response shaping.

    Returns
    -------
    dict[str, Any]
        ``status``, ``skill_briefings``, ``skill_count``,
        ``agent_instruction``, and next-step contract.
    """
    repo_path = Path(path).resolve()
    elapsed_ms = timed_call()
    params: dict[str, Any] = {
        "path": str(path),
        "cache_dir": cache_dir,
        "min_occurrences": min_occurrences,
        "min_confidence": min_confidence,
    }

    try:
        from drift_sdk.api._config import _emit_api_telemetry

        effective_cache = (
            Path(cache_dir) if cache_dir else repo_path / ".drift-cache"
        )
        store = ArchGraphStore(cache_dir=effective_cache)
        graph = store.load()

        if graph is None:
            return _error_response(
                "DRIFT-7003",
                "No architecture graph available. Run drift_scan or "
                "drift_map first to seed the graph.",
                recoverable=True,
            )

        briefings = generate_skill_briefings(
            graph,  # type: ignore[arg-type]
            min_occurrences=min_occurrences,
            min_confidence=min_confidence,
        )
        briefing_dicts = [b.to_dict() for b in briefings]
        agent_instruction = _build_agent_instruction(briefings)

        result: dict[str, Any] = {
            "status": "ok",
            "skill_briefings": briefing_dicts,
            "skill_count": len(briefing_dicts),
            "agent_instruction": agent_instruction,
            **_next_step_contract(
                next_tool="drift_steer",
                done_when="skills_created",
                fallback_tool="drift_scan",
            ),
        }

        _emit_api_telemetry(
            tool_name="api.generate_skills",
            params=params,
            status="ok",
            elapsed_ms=elapsed_ms(),
            result=result,
            error=None,
            repo_root=repo_path,
        )

        return shape_for_profile(result, response_profile)

    except Exception as exc:
        _log.debug("generate_skills() error: %s", exc, exc_info=True)
        try:
            from drift_sdk.api._config import _emit_api_telemetry

            _emit_api_telemetry(
                tool_name="api.generate_skills",
                params=params,
                status="error",
                elapsed_ms=elapsed_ms(),
                result=None,
                error=exc,
                repo_root=repo_path,
            )
        except Exception:
            pass
        return _error_response("DRIFT-7003", str(exc), recoverable=True)


def _build_agent_instruction(
    briefings: list[Any],
) -> str:
    """Build the agent instruction for skill creation."""
    if not briefings:
        return (
            "No recurring patterns qualify for skill generation. "
            "No modules have enough signal recurrence above threshold."
        )

    names = ", ".join(b.name for b in briefings)
    count = len(briefings)

    return (
        f"Create {count} SKILL.md file(s) under .github/skills/ for the "
        f"following modules: {names}.\n\n"
        "For each skill_briefing in the response, create a directory "
        ".github/skills/<name>/ and write a SKILL.md file with:\n\n"
        "1. YAML frontmatter: name, description (include trigger_signals "
        "as keywords), argument-hint.\n"
        "2. Section 'When To Use': derived from trigger_signals and "
        "hotspot_files — describe when this skill applies.\n"
        "3. Section 'Core Rules': one rule per constraint (enforcement "
        "level = severity). Add rules for each trigger_signal.\n"
        "4. Section 'Architecture Context': layer, neighbors, key "
        "abstractions — so the agent understands the module's role.\n"
        "5. Section 'Review Checklist': actionable items derived from "
        "constraints and trigger signals.\n"
        "6. Section 'References': link to relevant project docs.\n\n"
        "IMPORTANT: Use the structured data from skill_briefings — do NOT "
        "hallucinate constraints or signals not present in the briefing. "
        "Each constraint's enforcement level (block/warn/info) must be "
        "reflected in the rule severity."
    )

