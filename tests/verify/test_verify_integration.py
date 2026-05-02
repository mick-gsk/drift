"""Integration tests for drift verify CLI (CliRunner + subprocess)."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from drift_verify._cmd import evidence_cmd


class TestEvidenceCLI:
    def test_empty_diff_exits_zero(self, tmp_path: Path) -> None:
        diff_file = tmp_path / "empty.diff"
        diff_file.write_text("", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(
            evidence_cmd,
            ["--diff", str(diff_file), "--repo", str(tmp_path), "--format", "json", "--no-reviewer"],
        )
        assert result.exit_code == 0

    def test_json_output_is_valid_json(self, tmp_path: Path) -> None:
        diff_file = tmp_path / "empty.diff"
        diff_file.write_text("", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(
            evidence_cmd,
            ["--diff", str(diff_file), "--repo", str(tmp_path), "--format", "json", "--no-reviewer"],
        )
        data = json.loads(result.output)
        assert data["schema"] == "evidence-package-v1"
        assert "action_recommendation" in data

    def test_json_automerge_on_empty_diff(self, tmp_path: Path) -> None:
        diff_file = tmp_path / "empty.diff"
        diff_file.write_text("", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(
            evidence_cmd,
            ["--diff", str(diff_file), "--repo", str(tmp_path), "--format", "json", "--no-reviewer"],
        )
        data = json.loads(result.output)
        assert data["action_recommendation"]["verdict"] == "automerge"

    def test_sarif_output_has_runs(self, tmp_path: Path) -> None:
        diff_file = tmp_path / "empty.diff"
        diff_file.write_text("", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(
            evidence_cmd,
            ["--diff", str(diff_file), "--repo", str(tmp_path), "--format", "sarif", "--no-reviewer"],
        )
        data = json.loads(result.output)
        assert data["version"] == "2.1.0"
        assert "runs" in data

    def test_exit_zero_flag_overrides_code(self, tmp_path: Path) -> None:
        diff_file = tmp_path / "test.diff"
        diff_file.write_text("", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(
            evidence_cmd,
            ["--diff", str(diff_file), "--repo", str(tmp_path), "--format", "json", "--no-reviewer", "--exit-zero"],
        )
        assert result.exit_code == 0

    def test_missing_diff_file_allowed(self, tmp_path: Path) -> None:
        """Invoking without --diff should still work (empty diff by default)."""
        runner = CliRunner()
        result = runner.invoke(
            evidence_cmd,
            ["--repo", str(tmp_path), "--format", "json", "--no-reviewer"],
        )
        # No diff means empty, should automerge with exit 0
        assert result.exit_code == 0
