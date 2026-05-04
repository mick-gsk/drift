from __future__ import annotations

from click.testing import CliRunner

from drift import cli


def test_root_help_contains_ordered_stable_sections() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.main, ["--help"])

    assert result.exit_code == 0
    output = result.output
    assert "Start Here (80% Path):" in output
    assert "Investigation:" in output
    assert "Agent & MCP:" in output
    assert "CI & Automation:" in output
    assert output.index("Start Here (80% Path):") < output.index("Investigation:")


def test_help_nav_subcommand_is_exposed() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.main, ["--help"])

    assert result.exit_code == 0
    assert "help-nav" in result.output


def test_initial_view_line_caps_remain_readable() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.main, ["--help"], terminal_width=80)

    assert result.exit_code == 0
    lines = [line for line in result.output.splitlines() if line.strip()]
    assert len(lines) > 10
    assert max(len(line) for line in lines[:40]) <= 100
