"""Turn hits into short agent-facing text, and keep an honest session tally.

The counter only ever increments from a real hit produced by lookup.py.
Nothing here fabricates or estimates a number.
"""

from __future__ import annotations

import json
import pathlib

from drift.guard import lookup

MAX_MESSAGE_CHARS = 500
_KINDS = ("duplicate", "boundary")


def format_hits(hits: list[lookup.Hit]) -> str:
    """Compact message for the agent. Empty string when there is nothing to say."""
    if not hits:
        return ""
    lines = ["drift:"]
    for hit in hits:
        candidate = f"  - {hit.message}"
        projected = "\n".join(lines + [candidate])
        if len(projected) > MAX_MESSAGE_CHARS:
            lines.append("  - (more findings omitted)")
            break
        lines.append(candidate)
    text = "\n".join(lines)
    return text[:MAX_MESSAGE_CHARS]


def counter_path(repo_root) -> pathlib.Path:
    return pathlib.Path(repo_root) / ".drift" / "session_counter.json"


def read_counter(repo_root) -> dict:
    path = counter_path(repo_root)
    if not path.exists():
        return {kind: 0 for kind in _KINDS}
    try:
        with open(path, encoding="utf-8") as handle:
            stored = json.load(handle)
    except (OSError, ValueError):
        return {kind: 0 for kind in _KINDS}
    return {kind: int(stored.get(kind, 0)) for kind in _KINDS}


def bump(repo_root, kind: str, amount: int = 1) -> None:
    if kind not in _KINDS:
        return
    counts = read_counter(repo_root)
    counts[kind] += amount
    path = counter_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(counts, handle)


def reset_counter(repo_root) -> None:
    path = counter_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({kind: 0 for kind in _KINDS}, handle)


def summary_line(counts: dict) -> str:
    return (
        f"drift: {counts.get('duplicate', 0)} duplicate(s) flagged, "
        f"{counts.get('boundary', 0)} new boundary crossing(s) this session"
    )
