"""Amphetamin: what it holds open, and what it refuses to touch."""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys

from drift.guard import amphetamin

GUARD_SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "drift" / "guard"


def _executable_source(path: pathlib.Path) -> str:
    """The module without its docstrings.

    Checked with `ast` rather than by filtering lines: the docstrings in this
    module explain at length why it does not touch the permission system, and a
    line filter would read that explanation as the thing it forbids.
    """
    import ast

    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = node.body
        leads_with_a_string = (
            bool(body)
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        )
        if leads_with_a_string:
            node.body = body[1:] or [ast.Pass()]
    return ast.unparse(tree)


def test_off_by_default(tmp_path):
    """Nobody opts into a behaviour change by installing a plugin."""
    assert amphetamin.read_state(tmp_path)["enabled"] is False
    assert amphetamin.decide_stop(tmp_path, {"duplicate": 3}) is None


def test_holds_the_session_open_on_a_recorded_duplicate(tmp_path):
    amphetamin.set_enabled(tmp_path, True)

    verdict = amphetamin.decide_stop(tmp_path, {"duplicate": 2})

    assert verdict is not None
    assert verdict["decision"] == "block"
    assert "2 symbol(s)" in verdict["reason"]


def test_a_clean_tally_never_holds_the_session(tmp_path):
    """Silence is the default here too — no duplicates, no interference."""
    amphetamin.set_enabled(tmp_path, True)

    assert amphetamin.decide_stop(tmp_path, {"duplicate": 0, "boundary": 5}) is None


def test_it_blocks_once_and_then_lets_go(tmp_path):
    """A Stop hook that blocks repeatedly is a loop the user cannot escape."""
    amphetamin.set_enabled(tmp_path, True)

    first = amphetamin.decide_stop(tmp_path, {"duplicate": 1})
    second = amphetamin.decide_stop(tmp_path, {"duplicate": 1})
    third = amphetamin.decide_stop(tmp_path, {"duplicate": 9})

    assert first is not None
    assert second is None
    assert third is None


def test_switching_on_starts_the_run_from_zero(tmp_path):
    amphetamin.set_enabled(tmp_path, True)
    amphetamin.decide_stop(tmp_path, {"duplicate": 1})
    assert amphetamin.read_state(tmp_path)["continuations"] == 1

    amphetamin.set_enabled(tmp_path, True)

    assert amphetamin.read_state(tmp_path)["continuations"] == 0


def test_a_corrupt_state_file_does_not_break_the_session(tmp_path):
    amphetamin.set_enabled(tmp_path, True)
    amphetamin._state_file(tmp_path).write_text("{not json", encoding="utf-8")

    assert amphetamin.read_state(tmp_path)["enabled"] is False
    assert amphetamin.decide_stop(tmp_path, {"duplicate": 4}) is None


def test_it_never_touches_the_permission_system():
    """The prompt on `Read` is the user's only view of what an agent reaches for.

    Repository content is an established prompt-injection surface, so a plugin
    that auto-approves reads trades a real control for convenience. This test
    exists because the first draft of this module did exactly that.
    """
    code = _executable_source(GUARD_SRC / "amphetamin.py")

    for forbidden in ("permissionDecision", "PermissionRequest", "behavior"):
        assert forbidden not in code, (
            f"{forbidden} appears in amphetamin's executable code — this mode must never "
            "answer a permission prompt on the user's behalf"
        )


def test_the_stop_hook_emits_a_single_json_object(tmp_path, sample_repo):
    """Claude Code parses one JSON document from a hook, not two."""
    from drift.guard import build, report

    build.build_full(sample_repo)
    amphetamin.set_enabled(sample_repo, True)
    report.bump(sample_repo, "duplicate")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "drift.guard",
            "--hook",
            "Stop",
            "--repo",
            str(sample_repo),
            "stats",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["decision"] == "block"
    assert "reason" in payload
    assert "drift:" in payload["systemMessage"]


def test_a_quiet_session_still_reports_the_tally(tmp_path, sample_repo):
    from drift.guard import build

    build.build_full(sample_repo)
    amphetamin.set_enabled(sample_repo, True)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "drift.guard",
            "--hook",
            "Stop",
            "--repo",
            str(sample_repo),
            "stats",
        ],
        capture_output=True,
        text=True,
    )

    payload = json.loads(result.stdout)
    assert "decision" not in payload
    assert "drift:" in payload["systemMessage"]
