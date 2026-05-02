"""Tests for the committed drift configuration JSON schema."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from drift.cli import main
from drift.config import build_config_json_schema

REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "drift.schema.json"


def test_committed_schema_matches_config_model() -> None:
    committed = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    expected = build_config_json_schema()

    assert committed == expected, (
        "drift.schema.json is out of sync with DriftConfig. "
        "Regenerate with: drift config schema --output drift.schema.json"
    )


def test_config_schema_command_writes_expected_file(tmp_path: Path) -> None:
    runner = CliRunner()
    out_file = tmp_path / "drift.schema.json"

    result = runner.invoke(main, ["config", "schema", "--output", str(out_file)])

    assert result.exit_code == 0
    assert out_file.exists()
    assert json.loads(out_file.read_text(encoding="utf-8")) == build_config_json_schema()
