"""Turn hits into short agent-facing text, and keep an honest session tally.

The counter only ever increments from a real hit produced by lookup.py.
Nothing here fabricates or estimates a number.
"""

from __future__ import annotations

import json
import sqlite3

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


# The tally lives in the index database, not in a JSON file beside it.
#
# Claude Code fires PostToolUse once per tool call and therefore concurrently
# whenever the model batches independent calls — which amphetamin explicitly
# asks it to do. Read-modify-write on a JSON file loses those updates: measured
# with 200 increments across 8 threads, the file-backed counter ended at 6.
#
# SQLite makes the increment a single atomic statement, and the database is
# already open in this code path anyway. No index means no counting, which is
# correct: without one the guard has nothing to report either.
_COUNTER_KEY = "count_{kind}"


def _counter_connection(repo_root):
    conn = schema.connect(repo_root)
    if conn is None or not schema.is_usable(conn):
        if conn is not None:
            conn.close()
        return None
    return conn


def read_counter(repo_root) -> dict:
    conn = _counter_connection(repo_root)
    if conn is None:
        return {kind: 0 for kind in _KINDS}
    try:
        rows = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    except sqlite3.DatabaseError:
        return {kind: 0 for kind in _KINDS}
    finally:
        conn.close()

    counts = {}
    for kind in _KINDS:
        try:
            counts[kind] = int(rows.get(_COUNTER_KEY.format(kind=kind), 0))
        except (TypeError, ValueError):
            counts[kind] = 0
    return counts


def bump(repo_root, kind: str, amount: int = 1) -> None:
    if kind not in _KINDS:
        return
    conn = _counter_connection(repo_root)
    if conn is None:
        return
    try:
        conn.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?)"
            " ON CONFLICT(key) DO UPDATE SET value ="
            " CAST(CAST(value AS INTEGER) + ? AS TEXT)",
            (_COUNTER_KEY.format(kind=kind), str(amount), amount),
        )
        conn.commit()
    except sqlite3.DatabaseError:
        pass  # a guard that cannot count still must not break the session
    finally:
        conn.close()


def reset_counter(repo_root) -> None:
    conn = _counter_connection(repo_root)
    if conn is None:
        return
    try:
        conn.executemany(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, '0')",
            [(_COUNTER_KEY.format(kind=kind),) for kind in _KINDS],
        )
        conn.commit()
    except sqlite3.DatabaseError:
        pass
    finally:
        conn.close()


def summary_line(counts: dict) -> str:
    return (
        f"drift: {counts.get('duplicate', 0)} duplicate(s) flagged, "
        f"{counts.get('boundary', 0)} new boundary crossing(s) this session"
    )
