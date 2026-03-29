from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from drift.cli import main


def test_validate_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--help"])
    assert result.exit_code == 0
    assert "Validate drift config and environment" in result.output


def test_scan_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--help"])
    assert result.exit_code == 0
    assert "response-detail" in result.output


def test_fix_plan_help() -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["fix-plan", "--help"])
    assert result.exit_code == 0
    assert "automation-fit-min" in result.output


def test_validate_outputs_json(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["validate", "--repo", str(tmp_path)])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == "2.0"
    assert "valid" in payload
    assert "git_available" in payload


def test_scan_outputs_json(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(main, ["scan", "--repo", str(tmp_path), "--max-findings", "1"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == "2.0"
    assert "accept_change" in payload
    assert "blocking_reasons" in payload
