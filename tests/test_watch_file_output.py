"""Tests for ``drift watch --output`` file-output mode."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

# ---------------------------------------------------------------------------
# Shared fake nudge factory
# ---------------------------------------------------------------------------

def _make_fake_nudge(
    direction: str = "stable",
    delta: float = 0.0,
    safe: bool = True,
    new_findings: list | None = None,
    resolved: list | None = None,
) -> SimpleNamespace:
    def fake_nudge(*, path, changed_files=None, **_kwargs):
        return {
            "direction": direction,
            "delta": delta,
            "safe_to_commit": safe,
            "new_findings": new_findings or [],
            "resolved_findings": resolved or [],
            "auto_fast_path": True,
            "latency_exceeded": False,
        }

    return SimpleNamespace(nudge=fake_nudge)


def _iter_once_then_interrupt(changed: set):
    """Generator: yields *changed* once, then raises KeyboardInterrupt."""

    class _Iter:
        def __iter__(self):
            yield changed
            raise KeyboardInterrupt

    return _Iter()


def _patch_common(monkeypatch, tmp_path, nudge_ns, changes):
    """Apply common monkeypatches needed for watch invocations."""
    monkeypatch.setitem(sys.modules, "watchfiles", SimpleNamespace(
        watch=lambda *_a, **_kw: _iter_once_then_interrupt(changes)
    ))
    monkeypatch.setitem(sys.modules, "drift.api.nudge", nudge_ns)
    monkeypatch.setattr(
        "drift.config.DriftConfig.load",
        lambda *_a, **_kw: SimpleNamespace(exclude=[]),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_output_file_created_on_initial(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """--output file exists after initial baseline nudge, schema is correct."""
    from drift.commands.watch import watch

    src = tmp_path / "src"
    src.mkdir()
    (src / "a.py").write_text("x = 1\n", encoding="utf-8")

    output_file = tmp_path / ".drift" / "nudge.json"
    nudge_ns = _make_fake_nudge()

    # Provide one file change so the loop also runs, but we care about initial
    _patch_common(
        monkeypatch, tmp_path, nudge_ns,
        {(1, str(src / "a.py"))}
    )

    runner = CliRunner()
    result = runner.invoke(
        watch,
        ["--repo", str(tmp_path), "--debounce", "0.1", "--output", str(output_file)],
    )

    assert result.exit_code == 0
    assert output_file.exists(), "nudge.json must be created"

    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert data["schema_version"] == "1"
    assert "timestamp" in data
    assert data["error"] is None
    assert isinstance(data["safe_to_commit"], bool)


def test_output_updated_on_file_change(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """After a file change the JSON reflects direction, delta and changed_files."""
    from drift.commands.watch import watch

    src = tmp_path / "src"
    src.mkdir()
    (src / "b.py").write_text("y = 2\n", encoding="utf-8")

    output_file = tmp_path / "nudge.json"
    nudge_ns = _make_fake_nudge(direction="degrading", delta=-0.1, safe=False)

    _patch_common(
        monkeypatch, tmp_path, nudge_ns,
        {(1, str(src / "b.py"))}
    )

    runner = CliRunner()
    result = runner.invoke(
        watch,
        ["--repo", str(tmp_path), "--debounce", "0.1", "--output", str(output_file)],
    )

    assert result.exit_code == 0
    data = json.loads(output_file.read_text(encoding="utf-8"))

    # After the loop nudge, direction should be "degrading"
    assert data["direction"] == "degrading"
    assert data["delta"] == pytest.approx(-0.1)
    assert data["safe_to_commit"] is False
    assert data["initial"] is False
    assert "src/b.py" in data["changed_files"]


def test_output_directory_created_automatically(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Parent directories of --output are created automatically."""
    from drift.commands.watch import watch

    src = tmp_path / "src"
    src.mkdir()
    (src / "c.py").write_text("z = 3\n", encoding="utf-8")

    # Deeply nested path that doesn't exist yet
    output_file = tmp_path / "some" / "deep" / "dir" / "nudge.json"
    nudge_ns = _make_fake_nudge()

    _patch_common(monkeypatch, tmp_path, nudge_ns, {(1, str(src / "c.py"))})

    runner = CliRunner()
    result = runner.invoke(
        watch,
        ["--repo", str(tmp_path), "--debounce", "0.1", "--output", str(output_file)],
    )

    assert result.exit_code == 0
    assert output_file.exists(), "nested output path must be created"


def test_output_written_on_loop_nudge_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When nudge() raises during the loop, an error summary is written instead of crashing."""
    from drift.commands.watch import watch

    src = tmp_path / "src"
    src.mkdir()
    (src / "d.py").write_text("w = 4\n", encoding="utf-8")

    output_file = tmp_path / ".drift" / "nudge.json"

    call_count = 0

    def flaky_nudge(*, path, changed_files=None, **_kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Initial call succeeds
            return {
                "direction": "stable",
                "delta": 0.0,
                "safe_to_commit": True,
                "new_findings": [],
                "resolved_findings": [],
                "auto_fast_path": True,
                "latency_exceeded": False,
            }
        raise RuntimeError("simulated nudge failure")

    monkeypatch.setitem(
        sys.modules, "watchfiles",
        SimpleNamespace(watch=lambda *_a, **_kw: _iter_once_then_interrupt(
            {(1, str(src / "d.py"))}
        )),
    )
    monkeypatch.setitem(
        sys.modules, "drift.api.nudge",
        SimpleNamespace(nudge=flaky_nudge),
    )
    monkeypatch.setattr(
        "drift.config.DriftConfig.load",
        lambda *_a, **_kw: SimpleNamespace(exclude=[]),
    )

    runner = CliRunner()
    result = runner.invoke(
        watch,
        ["--repo", str(tmp_path), "--debounce", "0.1", "--output", str(output_file)],
    )

    # Watcher must NOT crash (exit 0 via KeyboardInterrupt path)
    assert result.exit_code == 0
    assert output_file.exists(), "error summary must still be written"

    data = json.loads(output_file.read_text(encoding="utf-8"))
    assert data["error"] is not None
    assert "simulated nudge failure" in data["error"]
    assert data["direction"] is None
    assert data["safe_to_commit"] is None


def test_no_output_file_without_flag(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Without --output no .drift/nudge.json is created."""
    from drift.commands.watch import watch

    src = tmp_path / "src"
    src.mkdir()
    (src / "e.py").write_text("v = 5\n", encoding="utf-8")

    nudge_ns = _make_fake_nudge()
    _patch_common(monkeypatch, tmp_path, nudge_ns, {(1, str(src / "e.py"))})

    runner = CliRunner()
    result = runner.invoke(
        watch,
        ["--repo", str(tmp_path), "--debounce", "0.1"],
    )

    assert result.exit_code == 0
    assert not (tmp_path / ".drift" / "nudge.json").exists()
