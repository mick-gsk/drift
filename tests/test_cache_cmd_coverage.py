"""Tests for commands/cache_cmd.py (19% coverage → 80%+).

Covers:
  - cache clear: default (both), parse-only, signal-only,
    dry-run, mutually exclusive flag error, empty cache dirs
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from click.testing import CliRunner


class TestCacheClearCommand:
    def _make_cache(
        self,
        tmp_path: Path,
        *,
        parse_count: int = 0,
        signal_count: int = 0,
    ) -> Path:
        """Create a fake .drift-cache with specified number of json entries."""
        cache_root = tmp_path / ".drift-cache"
        if parse_count > 0:
            parse_dir = cache_root / "parse"
            parse_dir.mkdir(parents=True)
            for i in range(parse_count):
                (parse_dir / f"entry_{i}.json").write_text("{}", encoding="utf-8")
        if signal_count > 0:
            signal_dir = cache_root / "signals"
            signal_dir.mkdir(parents=True)
            for i in range(signal_count):
                (signal_dir / f"entry_{i}.json").write_text("{}", encoding="utf-8")
        return cache_root

    def _invoke_clear(self, repo: Path, *extra_args: str):
        from drift.commands.cache_cmd import clear

        runner = CliRunner()
        return runner.invoke(clear, ["--repo", str(repo), *extra_args])

    def _patch_config(self, monkeypatch, cache_dir=".drift-cache"):
        """Monkeypatch DriftConfig.load to return a simple config."""
        import drift.config as config_mod

        _cache_dir = cache_dir

        def _fake_load(*_args, **_kwargs):
            return SimpleNamespace(cache_dir=_cache_dir)

        monkeypatch.setattr(config_mod.DriftConfig, "load", _fake_load)

    def test_clear_all_deletes_parse_and_signal_entries(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        self._patch_config(monkeypatch)
        self._make_cache(tmp_path, parse_count=3, signal_count=2)

        result = self._invoke_clear(tmp_path)

        assert result.exit_code == 0
        assert "3 parse" in result.output
        assert "2 signal" in result.output
        # entries should be gone
        parse_dir = tmp_path / ".drift-cache" / "parse"
        assert list(parse_dir.glob("*.json")) == []

    def test_parse_only_skips_signal_entries(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        self._patch_config(monkeypatch)
        self._make_cache(tmp_path, parse_count=2, signal_count=3)

        result = self._invoke_clear(tmp_path, "--parse-only")

        assert result.exit_code == 0
        assert "parse" in result.output
        # signal entries should still exist
        signal_dir = tmp_path / ".drift-cache" / "signals"
        assert len(list(signal_dir.glob("*.json"))) == 3

    def test_signal_only_skips_parse_entries(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        self._patch_config(monkeypatch)
        self._make_cache(tmp_path, parse_count=4, signal_count=1)

        result = self._invoke_clear(tmp_path, "--signal-only")

        assert result.exit_code == 0
        assert "signal" in result.output
        # parse entries should still exist
        parse_dir = tmp_path / ".drift-cache" / "parse"
        assert len(list(parse_dir.glob("*.json"))) == 4

    def test_mutually_exclusive_flags_raise_usage_error(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        self._patch_config(monkeypatch)

        result = self._invoke_clear(tmp_path, "--parse-only", "--signal-only")

        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_dry_run_reports_without_deleting(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        self._patch_config(monkeypatch)
        self._make_cache(tmp_path, parse_count=2, signal_count=2)

        result = self._invoke_clear(tmp_path, "--dry-run")

        assert result.exit_code == 0
        assert "dry-run" in result.output.lower() or "would" in result.output.lower()
        # files should NOT be deleted
        parse_dir = tmp_path / ".drift-cache" / "parse"
        assert len(list(parse_dir.glob("*.json"))) == 2

    def test_empty_cache_reports_zero_entries(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        self._patch_config(monkeypatch)
        # no cache directories created at all

        result = self._invoke_clear(tmp_path)

        assert result.exit_code == 0
        assert "0 parse" in result.output

    def test_singular_entry_word_used_for_one_item(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        self._patch_config(monkeypatch)
        self._make_cache(tmp_path, parse_count=1, signal_count=1)

        result = self._invoke_clear(tmp_path)

        assert result.exit_code == 0
        # "1 parse entry" (singular) should appear in output
        assert "1 parse entry" in result.output
        assert "1 signal entry" in result.output

    def test_plural_entries_word_used_for_multiple(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        self._patch_config(monkeypatch)
        self._make_cache(tmp_path, parse_count=5, signal_count=3)

        result = self._invoke_clear(tmp_path)

        assert result.exit_code == 0
        assert "5 parse entries" in result.output
        assert "3 signal entries" in result.output

    def test_dry_run_parse_only_reports_parse_only(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        self._patch_config(monkeypatch)
        self._make_cache(tmp_path, parse_count=2, signal_count=1)

        result = self._invoke_clear(tmp_path, "--dry-run", "--parse-only")

        assert result.exit_code == 0
        assert "parse" in result.output
        # signal entries untouched
        signal_dir = tmp_path / ".drift-cache" / "signals"
        assert len(list(signal_dir.glob("*.json"))) == 1
