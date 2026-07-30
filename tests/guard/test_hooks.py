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


def _bare_env():
    """An environment where nothing drift-related is installed or importable.

    This is what a user has after `/plugin install drift@drift` and nothing
    else: no `drift-guard` on PATH, no `drift` package, no PYTHONPATH.
    """
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("PYTHONPATH", "VIRTUAL_ENV", "CLAUDE_PLUGIN_ROOT")
    }
    env["PATH"] = "/usr/bin:/bin:/usr/sbin:/sbin"
    return env


def test_the_plugin_alone_is_enough(sample_repo):
    """A bare `/plugin install` must produce a working guard, with no pip step.

    The marketplace clones the repository, so the guard's source ships inside
    the installed plugin and runs from there under any system Python. Without
    that fallback a fresh install is silently inert: every hook exits 0 with no
    output, which is indistinguishable from a guard that never finds anything.
    """
    build.build_full(sample_repo)
    (sample_repo / "src" / "api" / "schemas.py").write_text(
        "def validate_token(token, audience):\n    return True\n", encoding="utf-8"
    )
    payload = {"tool_input": {"file_path": str(sample_repo / "src" / "api" / "schemas.py")}}

    result = subprocess.run(
        ["bash", str(HOOKS / "guard-post-edit.sh")],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=sample_repo,
        env=_bare_env(),
    )

    assert result.returncode == 0
    assert result.stdout.strip(), "the hook stayed silent with only the plugin installed"
    assert "validate_token" in json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]


def test_the_guard_imports_only_the_standard_library():
    """The bundled fallback works only as long as no third-party import creeps in."""
    env = _bare_env()
    env["PYTHONPATH"] = str(HOOKS.parent / "src")

    result = subprocess.run(
        [
            "python3",
            "-c",
            "import drift.guard.build, drift.guard.lookup, drift.guard.report; print('ok')",
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


def test_bin_wrapper_works_without_an_installed_package(sample_repo):
    """`/drift:doctor` calls `drift-guard` as a bare command; bin/ makes that real.

    Claude Code puts a plugin's bin/ on PATH. Without this wrapper the two slash
    commands only work for users who separately ran `pip install drift-analyzer`.

    The wrapper builds the index and then reports on it, both in a bare
    environment. It used to run `doctor` alone against the checkout itself,
    which passes only where a stray `.drift/` happens to sit next to the
    source: `_bare_env()` keeps `DRIFT_CACHE_HOME`, the fixture points it at an
    empty per-test directory, and `doctor` exits 1 on a missing index. On a
    fresh clone — the state every new contributor is in — that test failed.
    """
    wrapper = HOOKS.parent / "bin" / "drift-guard"

    assert wrapper.exists()
    assert os.access(wrapper, os.X_OK), "bin/drift-guard must be executable"

    built = subprocess.run(
        [str(wrapper), "--repo", str(sample_repo), "build"],
        capture_output=True,
        text=True,
        env=_bare_env(),
    )
    assert built.returncode == 0, built.stderr

    result = subprocess.run(
        [str(wrapper), "--repo", str(sample_repo), "doctor"],
        capture_output=True,
        text=True,
        env=_bare_env(),
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "index" in result.stdout


def test_plugin_manifest_is_not_version_pinned():
    """No `version` field, so every merge to main reaches installed users.

    Claude Code pins a plugin to the manifest's `version` string when one is
    present and only offers an update when that string changes. This repository
    releases through a channel that is not always available, so a pinned
    version means a fix can sit on main indefinitely while `plugin update`
    reports "already at latest". Without the field, Claude Code falls back to
    the git commit SHA.
    """
    root = pathlib.Path(__file__).resolve().parents[2]
    manifest = json.loads((root / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))

    assert "version" not in manifest, (
        "a pinned plugin version stops fixes from reaching users who already installed"
    )

    entry = json.loads((root / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    for plugin in entry["plugins"]:
        assert "version" not in plugin, f"{plugin['name']} is pinned in marketplace.json"


def test_slash_commands_are_named_the_way_the_documents_promise():
    """`commands/doctor.md` is invoked as `/drift:doctor`.

    The file name becomes the command name and the plugin name is already the
    namespace, so `drift-doctor.md` produced `/drift:drift-doctor`. Every
    document in this repository claimed `/drift:doctor` until it was tried in a
    real session, where Claude Code answered "Unknown command".
    """
    root = pathlib.Path(__file__).resolve().parents[2]
    names = {path.stem for path in (root / "commands").glob("*.md")}

    assert names == {"doctor", "stats", "amphetamin"}
    for name in names:
        assert not name.startswith("drift-"), (
            f"commands/{name}.md would be invoked as /drift:{name}, not /drift:"
            f"{name.removeprefix('drift-')}"
        )

    documented = (root / "README.md").read_text(encoding="utf-8")
    for name in names:
        assert f"/drift:{name}" in documented or name == "stats", (
            f"/drift:{name} is not the name the README promises"
        )
