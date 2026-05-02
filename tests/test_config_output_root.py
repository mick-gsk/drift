"""Tests for DriftConfig.output_root and resolve_artifact_path."""

from __future__ import annotations

from pathlib import Path

import pytest
from drift.config import DriftConfig


class TestOutputRootDefault:
    """Default behaviour: output_root=None keeps backward-compat repo-relative paths."""

    def test_resolve_artifact_path_default_is_repo_relative(self, tmp_path: Path) -> None:
        cfg = DriftConfig()
        assert cfg.output_root is None
        result = cfg.resolve_artifact_path(tmp_path, ".drift-cache")
        assert result == tmp_path / ".drift-cache"

    def test_resolve_artifact_path_nested_default(self, tmp_path: Path) -> None:
        cfg = DriftConfig()
        result = cfg.resolve_artifact_path(tmp_path, ".drift/feedback.jsonl")
        assert result == tmp_path / ".drift" / "feedback.jsonl"

    def test_cache_dir_still_goes_into_repo_root_by_default(self, tmp_path: Path) -> None:
        cfg = DriftConfig()
        result = cfg.resolve_artifact_path(tmp_path, cfg.cache_dir)
        assert result == tmp_path / ".drift-cache"


class TestOutputRootConfigField:
    """When output_root is set via drift.yaml, all artifact paths go there."""

    def test_resolve_artifact_path_uses_output_root(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "external_output"
        cfg = DriftConfig(output_root=str(out_dir))
        result = cfg.resolve_artifact_path(tmp_path / "myrepo", ".drift-cache")
        assert result == out_dir / ".drift-cache"
        # Must NOT be inside the repo
        assert tmp_path / "myrepo" not in result.parents

    def test_output_root_tilde_expansion(self, tmp_path: Path) -> None:
        cfg = DriftConfig(output_root="~/.drift")
        result = cfg.resolve_artifact_path(tmp_path, ".drift-cache")
        assert result == Path.home() / ".drift" / ".drift-cache"
        assert not str(result).startswith("~")

    def test_output_root_feedback_path(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "drift_out"
        cfg = DriftConfig(output_root=str(out_dir))
        result = cfg.resolve_artifact_path(tmp_path / "repo", ".drift/feedback.jsonl")
        assert result == out_dir / ".drift" / "feedback.jsonl"

    def test_output_root_loaded_from_yaml(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "artifacts"
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "drift.yaml").write_text(
            f"output_root: {out_dir}\n", encoding="utf-8"
        )
        cfg = DriftConfig.load(repo)
        assert cfg.output_root == str(out_dir)
        result = cfg.resolve_artifact_path(repo, cfg.cache_dir)
        assert result == out_dir / ".drift-cache"


class TestOutputRootEnvVar:
    """DRIFT_OUTPUT_ROOT env var acts as fallback when output_root is not configured."""

    def test_env_var_overrides_repo_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_dir = tmp_path / "env_output"
        monkeypatch.setenv("DRIFT_OUTPUT_ROOT", str(env_dir))
        cfg = DriftConfig()  # output_root is None
        result = cfg.resolve_artifact_path(tmp_path / "repo", ".drift-cache")
        assert result == env_dir / ".drift-cache"

    def test_config_field_takes_precedence_over_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        env_dir = tmp_path / "env_output"
        cfg_dir = tmp_path / "config_output"
        monkeypatch.setenv("DRIFT_OUTPUT_ROOT", str(env_dir))
        cfg = DriftConfig(output_root=str(cfg_dir))
        result = cfg.resolve_artifact_path(tmp_path / "repo", ".drift-cache")
        assert result == cfg_dir / ".drift-cache"
        assert env_dir not in result.parents

    def test_env_var_absent_falls_back_to_repo_path(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("DRIFT_OUTPUT_ROOT", raising=False)
        cfg = DriftConfig()
        result = cfg.resolve_artifact_path(tmp_path, ".drift/history")
        assert result == tmp_path / ".drift" / "history"
