"""Context-aware recommendation refinement based on reward scores.

Enriches recommendation text when the reward chain indicates low
fix-speed or specificity — no LLM, purely rule-based string operations.
"""

from __future__ import annotations

import re
from copy import deepcopy

from drift.models import Finding
from drift.recommendations import Recommendation
from drift.reward_chain import RewardScore

# Generic verbs to replace with concrete imperatives (F-12)
_GENERIC_VERB_MAP: dict[str, str] = {
    "consider": "extract",
    "review": "inspect",
    "ensure": "verify",
    "evaluate": "measure",
    "assess": "measure",
    "investigate": "trace",
    "examine": "inspect",
}

_GENERIC_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(v) for v in _GENERIC_VERB_MAP) + r")\b",
    re.IGNORECASE,
)

# Context-specific suffixes (F-13)
# Context-specific suffixes (F-13)
# Each tuple is (dedup_marker, full_suffix).  The dedup_marker is a short,
# stable substring embedded in the suffix itself for idempotent appending.
_CONTEXT_SUFFIXES: dict[str, tuple[str, str]] = {
    "test": (
        "this is test code",
        " Note: this is test code — the pattern may matter for "
        "test maintainability rather than production quality.",
    ),
    "generated": (
        "this is generated code",
        " Note: this is generated code — regenerating from the "
        "source template is often preferable to manual fixes.",
    ),
    "fixture": (
        "this is fixture/test-support code",
        " Note: this is fixture/test-support code — the finding may "
        "be acceptable if it serves test isolation.",
    ),
}


def refine(
    rec: Recommendation,
    finding: Finding,
    reward: RewardScore,
    *,
    max_iterations: int = 2,
) -> Recommendation:
    """Return a refined copy of *rec* based on reward feedback.

    The original ``rec`` object is never mutated (F-15).  At most
    *max_iterations* refinement passes are applied (F-14).
    If ``reward.total >= 0.7`` the recommendation is already good
    enough and is returned unchanged.

    Parameters
    ----------
    rec:
        The original recommendation.
    finding:
        The finding that produced the recommendation.
    reward:
        Reward score from ``compute_reward()``.
    max_iterations:
        Maximum refinement passes (default 2, F-14).
    """
    # Good enough — skip refinement
    if reward.total >= 0.7:
        return rec

    refined = deepcopy(rec)
    iterations = 0

    # --- Iteration 1: enrich with file/symbol when fix_speed is low (F-11)
    if iterations < max_iterations and reward.breakdown.get("fix_speed", 1.0) < 0.3:
        refined.description = _enrich_location(refined.description, finding)
        iterations += 1

    # --- Iteration 2: replace generic verbs (F-12)
    if iterations < max_iterations and reward.breakdown.get("specificity", 1.0) < 0.3:
        refined.description = _replace_generic_verbs(refined.description)
        iterations += 1

    # --- Context suffix (F-13) — applied once regardless of iteration count
    context = finding.finding_context or "production"
    entry = _CONTEXT_SUFFIXES.get(context)
    if entry is not None:
        marker, suffix = entry
        if marker not in refined.description:
            refined.description = refined.description.rstrip(".") + "." + suffix

    return refined


def _enrich_location(description: str, finding: Finding) -> str:
    """Prepend concrete file and symbol info to the description."""
    parts: list[str] = []

    if finding.file_path:
        parts.append(f"In {finding.file_path.as_posix()}")

    symbol = finding.symbol
    if not symbol and finding.logical_location:
        symbol = finding.logical_location.name
    if symbol:
        parts.append(f"symbol '{symbol}'")

    if finding.start_line and finding.start_line > 0:
        parts.append(f"line {finding.start_line}")

    if parts:
        prefix = ", ".join(parts) + ": "
        # Avoid double-prefixing
        if prefix not in description:
            description = prefix + description[0].lower() + description[1:]

    return description


def _replace_generic_verbs(description: str) -> str:
    """Replace generic verbs with concrete imperatives."""

    def _replacer(match: re.Match[str]) -> str:
        word = match.group(0)
        replacement = _GENERIC_VERB_MAP.get(word.lower(), word)
        # Preserve original casing
        if word[0].isupper():
            return replacement.capitalize()
        return replacement

    return _GENERIC_PATTERN.sub(_replacer, description)
