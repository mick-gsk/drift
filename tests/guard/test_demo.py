"""The 30-second demo must keep working.

README.md invites people to run `bash demos/guard-in-30-seconds.sh` as the
proof that any of this is real. A demo that rots is worse than no demo: it
turns the one artifact meant to establish trust into the thing that destroys
it. So the demo runs here, on every test run, against the real hook.
"""

from __future__ import annotations

import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEMO = ROOT / "demos" / "guard-in-30-seconds.sh"


def _run_demo(tmp_path):
    env = dict(os.environ)
    env["DRIFT_CACHE_HOME"] = str(tmp_path / "cache")
    return subprocess.run(
        ["bash", str(DEMO)],
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=env,
        timeout=120,
    )


def test_demo_is_executable():
    assert DEMO.exists(), "README points at this script"
    assert os.access(DEMO, os.X_OK)


def test_demo_finds_the_python_symbol_from_go(tmp_path):
    """The claim the demo exists to prove: a match across a language boundary."""
    result = _run_demo(tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "ValidateToken" in result.stdout
    assert "already exists as" in result.stdout
    assert "validate_token" in result.stdout
    assert "src/auth/tokens.py" in result.stdout


def test_demo_fails_loudly_when_the_guard_says_nothing():
    """Silence must never read as success.

    A demo that prints an empty section and exits 0 would let a broken guard
    ship behind a green test. The script checks its own output and exits 1.
    """
    source = DEMO.read_text(encoding="utf-8")

    assert 'if [ -z "$out" ]; then' in source
    assert "exit 1" in source


def test_demo_never_touches_the_real_index_cache():
    """Running a demo must not disturb the indexes a user already has."""
    source = DEMO.read_text(encoding="utf-8")

    assert "export DRIFT_CACHE_HOME=" in source
    assert 'trap ' in source and "rm -rf" in source, "the temporary tree is cleaned up"
