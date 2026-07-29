"""Tests for scripts/integrate_changelog_entry.py.

Regression cover for the post-commit hook writing entries under an
already-released version. See issue #761: the hook read the version from
pyproject.toml, which still carries the last released version after a
release, so a commit made after v2.51.1 shipped produced a *second*
``## [2.51.1]`` block dated today.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "integrate_changelog_entry.py"

_spec = importlib.util.spec_from_file_location("integrate_changelog_entry", _SCRIPT_PATH)
assert _spec and _spec.loader
_script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_script)  # type: ignore[union-attr]


_EXISTING = """## [2.51.1] - 2026-05-04

Short version: Something already shipped.

### Fixed

- An earlier fix

"""


@pytest.fixture
def changelog(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "CHANGELOG.md"
    path.write_text(_EXISTING, encoding="utf-8")
    monkeypatch.setattr(_script, "REPO_ROOT", tmp_path)
    return path


def _integrate(**kwargs: Any) -> bool:
    return bool(_script.integrate(**kwargs))


def test_released_version_targets_unreleased(monkeypatch: pytest.MonkeyPatch) -> None:
    """A tagged pyproject version must route entries to Unreleased."""
    monkeypatch.setattr(_script, "_read_version", lambda: "2.51.1")
    monkeypatch.setattr(_script, "_is_released", lambda _v: True)
    assert _script._target_version() == "Unreleased"


def test_unreleased_version_targets_itself(monkeypatch: pytest.MonkeyPatch) -> None:
    """An untagged version is still in flight and keeps its own heading."""
    monkeypatch.setattr(_script, "_read_version", lambda: "2.52.0")
    monkeypatch.setattr(_script, "_is_released", lambda _v: False)
    assert _script._target_version() == "2.52.0"


def test_does_not_duplicate_a_released_version_block(changelog: Path) -> None:
    """The bug from #761: a second block for an already-released version."""
    _integrate(
        commit_type="chore",
        message="make .githooks executable",
        version="Unreleased",
        changelog=changelog,
    )
    text = changelog.read_text(encoding="utf-8")
    assert text.count("## [2.51.1]") == 1, "released version block was duplicated"
    assert "## [Unreleased]" in text
    assert text.index("## [Unreleased]") < text.index("## [2.51.1]")


def test_generated_block_has_no_duplicated_summary(changelog: Path) -> None:
    """The message must not appear as both 'Short version' and a bullet."""
    message = "make .githooks executable"
    _integrate(
        commit_type="chore",
        message=message,
        version="Unreleased",
        changelog=changelog,
    )
    text = changelog.read_text(encoding="utf-8")
    assert f"Short version: {message}" not in text
    assert text.count(message) == 1


def test_unreleased_heading_carries_no_date(changelog: Path) -> None:
    """Unreleased is not a release, so it must not be dated."""
    _integrate(
        commit_type="fix",
        message="some fix",
        version="Unreleased",
        changelog=changelog,
    )
    heading = next(
        line for line in changelog.read_text(encoding="utf-8").splitlines()
        if line.startswith("## [Unreleased]")
    )
    assert heading.strip() == "## [Unreleased]"


def test_second_entry_appends_to_same_unreleased_block(changelog: Path) -> None:
    """Consecutive commits must not each open their own Unreleased block."""
    _integrate(commit_type="chore", message="first", version="Unreleased", changelog=changelog)
    _integrate(commit_type="fix", message="second", version="Unreleased", changelog=changelog)
    text = changelog.read_text(encoding="utf-8")
    assert text.count("## [Unreleased]") == 1
    assert "- first" in text
    assert "- second" in text


def test_repeated_entry_is_skipped(changelog: Path) -> None:
    """Re-running the hook for the same commit must be a no-op."""
    _integrate(commit_type="fix", message="same", version="Unreleased", changelog=changelog)
    second = _integrate(
        commit_type="fix", message="same", version="Unreleased", changelog=changelog
    )
    assert second is False
    assert changelog.read_text(encoding="utf-8").count("- same") == 1


def test_generated_sections_are_markdownlint_shaped(changelog: Path) -> None:
    """Headings need a blank line after them (MD022) — both code paths."""
    _integrate(commit_type="chore", message="first", version="Unreleased", changelog=changelog)
    _integrate(commit_type="fix", message="second", version="Unreleased", changelog=changelog)
    lines = changelog.read_text(encoding="utf-8").splitlines()
    for i, line in enumerate(lines[:-1]):
        if line.startswith("### "):
            assert lines[i + 1].strip() == "", f"missing blank line after {line!r}"
