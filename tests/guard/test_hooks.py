"""The shell hooks that Claude Code invokes.

These tests are about one thing: does what the guard found actually reach the
model? A hook that exits 0 and prints plain text reaches the transcript only,
so "something was printed" is not evidence the guard worked. Every assertion
here goes through the JSON envelope Claude Code reads.
"""

import json
import os
import pathlib
import subprocess
import sys

from drift.guard import build

HOOKS = pathlib.Path(__file__).resolve().parents[2] / "hooks"


def _env():
    """Make the interpreter running the tests reachable from inside the hook.

    The hooks resolve `drift-guard` from PATH; under pytest that binary lives in
    the same directory as the interpreter, which is not necessarily on PATH.
    """
    env = dict(os.environ)
    env["PATH"] = str(pathlib.Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    return env


def _run_hook(name, payload, cwd):
    return subprocess.run(
        ["bash", str(HOOKS / name)],
        input="" if payload is None else json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=cwd,
        env=_env(),
    )


def _agent_text(result):
    """The text Claude actually receives, or "" when the hook stayed silent."""
    if not result.stdout.strip():
        return ""
    payload = json.loads(result.stdout)
    return payload.get("hookSpecificOutput", {}).get("additionalContext", "")


def test_post_edit_hook_delivers_the_duplicate_to_the_model(sample_repo):
    build.build_full(sample_repo)
    (sample_repo / "src" / "api" / "schemas.py").write_text(
        "def validate_token(token, audience):\n    return True\n", encoding="utf-8"
    )

    result = _run_hook(
        "guard-post-edit.sh",
        {"tool_input": {"file_path": str(sample_repo / "src" / "api" / "schemas.py")}},
        cwd=sample_repo,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "validate_token" in payload["hookSpecificOutput"]["additionalContext"]


def test_pre_edit_hook_briefs_the_model_on_a_new_file(sample_repo):
    build.build_full(sample_repo)

    result = _run_hook(
        "guard-pre-edit.sh",
        {"tool_input": {"file_path": str(sample_repo / "src" / "api" / "brand_new.py")}},
        cwd=sample_repo,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "src/api" in payload["hookSpecificOutput"]["additionalContext"]


def test_pre_edit_hook_stays_silent_on_an_existing_file(sample_repo):
    """Editing what already exists is the common case; the guard must not talk."""
    build.build_full(sample_repo)

    result = _run_hook(
        "guard-pre-edit.sh",
        {"tool_input": {"file_path": str(sample_repo / "src" / "api" / "routes.py")}},
        cwd=sample_repo,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_stop_hook_reports_the_tally_to_the_user_not_the_model(sample_repo):
    build.build_full(sample_repo)

    result = _run_hook("guard-stop.sh", {}, cwd=sample_repo)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert "drift:" in payload["systemMessage"]
    assert "hookSpecificOutput" not in payload


def test_session_start_hook_briefs_the_model_once(sample_repo):
    build.build_full(sample_repo)

    result = _run_hook("guard-session-start.sh", {}, cwd=sample_repo)

    assert result.returncode == 0
    assert "drift guard is active" in _agent_text(result)


def test_hooks_exit_zero_on_garbage_input(sample_repo):
    result = subprocess.run(
        ["bash", str(HOOKS / "guard-post-edit.sh")],
        input="not json at all",
        capture_output=True,
        text=True,
        cwd=sample_repo,
        env=_env(),
    )

    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_hooks_ignore_non_python_files(sample_repo):
    build.build_full(sample_repo)

    result = _run_hook(
        "guard-post-edit.sh",
        {"tool_input": {"file_path": str(sample_repo / "README.md")}},
        cwd=sample_repo,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == ""


def test_every_hook_script_is_executable():
    """Claude Code silently skips a hook whose script lacks the x bit."""
    scripts = sorted(HOOKS.glob("guard-*.sh"))

    assert scripts, "no hook scripts found"
    for script in scripts:
        assert os.access(script, os.X_OK), f"{script.name} is not executable"


def test_hook_config_points_at_scripts_that_exist():
    root = pathlib.Path(__file__).resolve().parents[2]
    config = json.loads((root / "hooks" / "hooks.json").read_text(encoding="utf-8"))

    referenced = [
        entry["command"]
        for matchers in config["hooks"].values()
        for matcher in matchers
        for entry in matcher["hooks"]
    ]

    assert referenced
    for command in referenced:
        relative = command.strip('"').replace("${CLAUDE_PLUGIN_ROOT}/", "")
        assert (root / relative).exists(), f"{relative} is referenced but missing"
