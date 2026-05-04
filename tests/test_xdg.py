"""Tests for XDG Base Directory cache resolution."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from drift_config._xdg import (
    resolve_cache_dir,
    resolve_state_dir,
    xdg_cache_home,
)


class TestXdgCacheHome:
    def test_respects_xdg_cache_home_env(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"XDG_CACHE_HOME": str(tmp_path)}, clear=False):
            if sys.platform != "win32":
                assert xdg_cache_home() == tmp_path

    def test_falls_back_to_home_cache_on_unix(self) -> None:
        if sys.platform == "win32":
            pytest.skip("Unix-only test")
        env = {k: v for k, v in os.environ.items() if k != "XDG_CACHE_HOME"}
        with patch.dict(os.environ, env, clear=True):
            result = xdg_cache_home()
            assert result == Path.home() / ".cache"

    def test_windows_uses_localappdata(self, tmp_path: Path) -> None:
        if sys.platform != "win32":
            pytest.skip("Windows-only test")
        with patch.dict(os.environ, {"LOCALAPPDATA": str(tmp_path)}):
            assert xdg_cache_home() == tmp_path


class TestResolveCacheDir:
    def test_empty_configured_uses_xdg_when_no_legacy(self, tmp_path: Path) -> None:
        """No .drift-cache → XDG default."""
        result = resolve_cache_dir(tmp_path, "")
        assert result.is_absolute()
        assert "drift" in result.parts

    def test_empty_configured_uses_legacy_when_present(self, tmp_path: Path) -> None:
        """Existing .drift-cache dir → keep using it (migration compat)."""
        legacy = tmp_path / ".drift-cache"
        legacy.mkdir()
        result = resolve_cache_dir(tmp_path, "")
        assert result == legacy

    def test_explicit_relative_is_repo_relative(self, tmp_path: Path) -> None:
        result = resolve_cache_dir(tmp_path, "my-cache")
        assert result == (tmp_path / "my-cache").resolve()

    def test_explicit_absolute_is_used_as_is(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            abs_path = str(Path(tmp).resolve())
            result = resolve_cache_dir(Path("/some/repo"), abs_path)
            assert result == Path(abs_path)

    def test_xdg_paths_are_namespaced_by_repo(self, tmp_path: Path) -> None:
        """Two different repos should get distinct XDG cache dirs."""
        repo_a = tmp_path / "repo_a"
        repo_b = tmp_path / "repo_b"
        repo_a.mkdir()
        repo_b.mkdir()
        result_a = resolve_cache_dir(repo_a, "")
        result_b = resolve_cache_dir(repo_b, "")
        assert result_a != result_b

    def test_same_repo_always_resolves_same_path(self, tmp_path: Path) -> None:
        """Deterministic: same repo → same XDG cache dir."""
        result1 = resolve_cache_dir(tmp_path, "")
        result2 = resolve_cache_dir(tmp_path, "")
        assert result1 == result2


class TestResolveStateDir:
    def test_empty_configured_uses_xdg_state_when_no_legacy(self, tmp_path: Path) -> None:
        result = resolve_state_dir(tmp_path, "")
        assert result.is_absolute()
        assert "drift" in result.parts

    def test_legacy_drift_dir_is_preserved(self, tmp_path: Path) -> None:
        legacy = tmp_path / ".drift"
        legacy.mkdir()
        result = resolve_state_dir(tmp_path, "")
        assert result == legacy

    def test_cache_and_state_are_different_dirs(self, tmp_path: Path) -> None:
        cache = resolve_cache_dir(tmp_path, "")
        state = resolve_state_dir(tmp_path, "")
        assert cache != state
