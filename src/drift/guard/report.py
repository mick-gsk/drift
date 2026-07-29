"""Turn hits into short agent-facing text, and keep an honest session tally.

The counter only ever increments from a real hit produced by lookup.py.
Nothing here fabricates or estimates a number.
"""

from __future__ import annotations

import json
import pathlib

from drift.guard import lookup, schema

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


def hook_json(event: str, agent_text: str = "", user_text: str = "") -> str:
    """Wrap guard output in the envelope Claude Code reads.

    This is not cosmetic. A hook that exits 0 and writes plain stdout reaches
    the transcript only — the model never sees it. The one documented way into
    the model's context is `hookSpecificOutput.additionalContext`, so the
    guard's entire promise depends on this envelope. `systemMessage` is the
    separate channel for text meant for the human (the session tally).

    Returns "" when there is nothing to say, so silence stays the default.
    """
    payload: dict = {}
    if agent_text:
        payload["hookSpecificOutput"] = {
            "hookEventName": event,
            "additionalContext": agent_text,
        }
    if user_text:
        payload["systemMessage"] = user_text
    return json.dumps(payload) if payload else ""


def counter_path(repo_root) -> pathlib.Path:
    # Same directory as the index, so the guard leaves exactly one place behind
    # and `.drift/` never appears in a repository that did not ask for it.
    return schema.state_dir(repo_root) / "session_counter.json"


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
