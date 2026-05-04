"""CLI integration tests for drift cockpit (T017/T040)."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
from drift_cockpit._cmd import cockpit_cmd


class TestBuildCmd:
    def test_build_json_no_findings(self, tmp_path: Path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cockpit_cmd,
                [
                    "build",
                    "--pr", "PR-test",
                    "--format", "json",
                    "--exit-zero",
                ],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        output = result.output
        assert "decision-bundle-v1" in output
        assert "PR-test" in output
        assert "no_go" in output  # no evidence → no_go

    def test_build_sarif_format(self, tmp_path: Path):
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmp_path):
            result = runner.invoke(
                cockpit_cmd,
                ["build", "--pr", "PR-sarif", "--format", "sarif", "--exit-zero"],
                catch_exceptions=False,
            )
        assert result.exit_code == 0
        assert "2.1.0" in result.output


class TestDecideCmd:
    def test_decide_agree_creates_entry(self, tmp_path: Path):
        runner = CliRunner()
        result = runner.invoke(
            cockpit_cmd,
            [
                "decide",
                "--pr", "PR-decide",
                "--verdict", "go",
                "--recommendation", "go",
                "--actor", "test_user",
                "--ledger-dir", str(tmp_path),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "PR-decide" in result.output

    def test_decide_override_without_justification_fails(self, tmp_path: Path):
        runner = CliRunner()
        result = runner.invoke(
            cockpit_cmd,
            [
                "decide",
                "--pr", "PR-override",
                "--verdict", "go",
                "--recommendation", "no_go",
                # Missing --justification
                "--ledger-dir", str(tmp_path),
            ],
        )
        assert result.exit_code == 10

    def test_decide_override_with_justification_succeeds(self, tmp_path: Path):
        runner = CliRunner()
        result = runner.invoke(
            cockpit_cmd,
            [
                "decide",
                "--pr", "PR-justified",
                "--verdict", "go",
                "--recommendation", "no_go",
                "--justification", "Director approved low-risk exception.",
                "--ledger-dir", str(tmp_path),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0


class TestOutcomeCmd:
    def test_outcome_no_ledger_fails(self, tmp_path: Path):
        runner = CliRunner()
        result = runner.invoke(
            cockpit_cmd,
            ["outcome", "--pr", "PR-ghost", "--days", "7", "--ledger-dir", str(tmp_path)],
        )
        assert result.exit_code == 10

    def test_outcome_after_decide(self, tmp_path: Path):
        runner = CliRunner()
        # First create a ledger entry
        runner.invoke(
            cockpit_cmd,
            [
                "decide",
                "--pr", "PR-full",
                "--verdict", "go",
                "--recommendation", "go",
                "--ledger-dir", str(tmp_path),
            ],
        )
        # Then record an outcome
        result = runner.invoke(
            cockpit_cmd,
            [
                "outcome",
                "--pr", "PR-full",
                "--days", "7",
                "--state", "captured",
                "--rework-events", "0",
                "--ledger-dir", str(tmp_path),
            ],
            catch_exceptions=False,
        )
        assert result.exit_code == 0
        assert "7d" in result.output
