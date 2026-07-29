"""Amphetamin — keep the agent working, without making it careless.

The name promises speed. How that speed is bought matters more than the
promise, so this module is explicit about what it will not do:

* It does not skip permission prompts. An earlier draft auto-approved
  "non-mutating" tools at the `PermissionRequest` hook. That was wrong. The
  prompt on `Read` is the user's only view of what an agent reaches for, and
  repository content is an established prompt-injection surface — an agent
  steered by a file it just read can ask for `~/.ssh/id_rsa` or `.env`. A
  public plugin that removes that prompt weakens a real control in exchange
  for convenience.
* It does not truncate reads, shorten plans, skip verification or lower any
  threshold. Those buy a measurable win with an unmeasurable loss, and the
  loss lands on the user long after the win was noticed.

What is left is the honest version of "works longer": the agent stops early
far more often than it works slowly, and most early stops happen with work
still on the table. So this mode refuses exactly one stop per session, and
only when the guard's own index says something concrete was left behind.

That criterion is a fact, not a judgement about whether an answer "felt"
finished. A mode that argues with the model about intent burns turns; a mode
that points at a recorded duplicate gets a specific, finishable instruction.
"""

from __future__ import annotations

import json
import pathlib

from drift.guard import schema

#: One continuation per session. A Stop hook that blocks repeatedly is a loop,
#: not a mode, and the user cannot easily get out of one.
MAX_CONTINUATIONS = 1

_DEFAULT_STATE: dict = {"enabled": False, "continuations": 0, "blocked_for": 0}


def _state_file(repo_root) -> pathlib.Path:
    return schema.state_dir(repo_root) / "amphetamin.json"


def read_state(repo_root) -> dict:
    path = _state_file(repo_root)
    if not path.exists():
        return dict(_DEFAULT_STATE)
    try:
        with open(path, encoding="utf-8") as handle:
            stored = json.load(handle)
    except (OSError, ValueError):
        return dict(_DEFAULT_STATE)
    return {
        "enabled": bool(stored.get("enabled", False)),
        "continuations": int(stored.get("continuations", 0)),
        "blocked_for": int(stored.get("blocked_for", 0)),
    }


def write_state(repo_root, state: dict) -> None:
    path = _state_file(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle)


def set_enabled(repo_root, enabled: bool) -> dict:
    """Turn the mode on or off, and start the new run from zero."""
    state = read_state(repo_root)
    state["enabled"] = enabled
    state["continuations"] = 0
    state["blocked_for"] = 0
    write_state(repo_root, state)
    return state


def reset_run(repo_root) -> None:
    """Clear the per-session counters without changing the on/off choice."""
    state = read_state(repo_root)
    state["continuations"] = 0
    state["blocked_for"] = 0
    write_state(repo_root, state)


def decide_stop(repo_root, counts: dict) -> dict | None:
    """Block one stop when the session left machine-checked work behind.

    Returns None — meaning "let it stop" — whenever the mode is off, the
    session already used its one continuation, or the tally is clean. Silence
    is the default here exactly as it is everywhere else in the guard.
    """
    state = read_state(repo_root)
    if not state["enabled"]:
        return None
    if state["continuations"] >= MAX_CONTINUATIONS:
        return None

    duplicates = int(counts.get("duplicate", 0))
    if duplicates <= 0:
        return None

    state["continuations"] += 1
    state["blocked_for"] = duplicates
    write_state(repo_root, state)

    return {
        "decision": "block",
        "reason": (
            f"drift recorded {duplicates} symbol(s) introduced in this session that already "
            "existed elsewhere in this repository. Before finishing, for each one: reuse the "
            "existing definition, or state in one line why a second definition belongs here. "
            "If you have already done that, say so in one line and stop — this check fires "
            "once per session and will not ask again."
        ),
    }


def status_line(state: dict) -> str:
    if not state["enabled"]:
        return "amphetamin: off — `drift-guard amph on` to keep sessions running on open work"
    if state["continuations"]:
        return (
            f"amphetamin: on · held the session open once for "
            f"{state['blocked_for']} unresolved duplicate(s)"
        )
    return "amphetamin: on · nothing left open this session"
