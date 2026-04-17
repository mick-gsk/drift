"""Regression tests for issue #455: top-level first_run schema contract."""

from __future__ import annotations

import json
from pathlib import Path


def test_output_schema_declares_first_run_top_level_property() -> None:
    schema = json.loads(Path("drift.output.schema.json").read_text(encoding="utf-8"))

    properties = schema["properties"]
    assert "first_run" in properties

    first_run = properties["first_run"]
    assert first_run["type"] == ["object", "null"]


def test_output_schema_declares_first_run_core_fields() -> None:
    schema = json.loads(Path("drift.output.schema.json").read_text(encoding="utf-8"))

    first_run_props = schema["properties"]["first_run"]["properties"]

    assert "headline" in first_run_props
    assert "why_this_matters" in first_run_props
    assert "next_step" in first_run_props
    assert "top_findings" in first_run_props