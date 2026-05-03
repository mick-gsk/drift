from __future__ import annotations

from click.testing import CliRunner

from drift import cli

LEGACY_COMMANDS = [
    "status",
    "setup",
    "analyze",
    "check",
    "scan",
    "diff",
    "serve",
    "validate",
]


def test_legacy_commands_remain_callable() -> None:
    runner = CliRunner()

    for command_name in LEGACY_COMMANDS:
        result = runner.invoke(cli.main, [command_name, "--help"])
        assert result.exit_code == 0, f"command '{command_name}' should stay callable"


def test_help_nav_command_renders_grouped_navigation() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.main, ["help-nav"])

    assert result.exit_code == 0
    output = result.output
    assert "Start Here (80% Path):" in output
    assert "Investigation:" in output


def test_help_nav_area_filter_and_narrow_widths() -> None:
    runner = CliRunner()

    area_result = runner.invoke(cli.main, ["help-nav", "--area", "investigation"])
    assert area_result.exit_code == 0
    assert "Investigation:" in area_result.output
    assert "Start Here (80% Path):" not in area_result.output

    for width in (80, 60, 40):
        result = runner.invoke(cli.main, ["--help"], terminal_width=width)
        assert result.exit_code == 0
        assert "Start Here (80% Path):" in result.output
