"""Shared fixtures for guard tests."""

from __future__ import annotations

import json
import pathlib
import shutil

import pytest

FIXTURE_ROOT = pathlib.Path(__file__).parent / "fixtures" / "sample_repo"


@pytest.fixture(autouse=True)
def guard_cache_home(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """Keep every test's index out of the real user cache.

    The guard stores its index under the user's cache directory rather than in
    the analysed repository, so without this the suite would write into
    ~/.cache/drift and leak state between runs.
    """
    cache = tmp_path / "guard-cache"
    monkeypatch.setenv("DRIFT_CACHE_HOME", str(cache))
    return cache


@pytest.fixture
def sample_repo(tmp_path: pathlib.Path) -> pathlib.Path:
    """A writable copy of the ground-truth repo."""
    target = tmp_path / "sample_repo"
    shutil.copytree(FIXTURE_ROOT, target)
    return target


@pytest.fixture
def expected() -> dict:
    """The ground-truth expectations for gate G3."""
    with open(FIXTURE_ROOT / "expected.json", encoding="utf-8") as handle:
        return json.load(handle)
