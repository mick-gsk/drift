from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "ab_harness.py"


def load_ab_harness_module() -> Any:
    spec = importlib.util.spec_from_file_location("ab_harness", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["ab_harness"] = module
    spec.loader.exec_module(module)
    return module


def test_report_records_neutral_mock_mode_interpretation(tmp_path: Path) -> None:
    module = load_ab_harness_module()
    work_dir = tmp_path / "ab_harness"
    work_dir.mkdir()
    module.WORK_DIR = work_dir
    module.OUTCOMES_FILE = work_dir / "outcomes.json"
    module.REPORT_FILE = work_dir / "report.json"
    module.OUTCOMES_FILE.write_text(
        json.dumps({"outcomes": [{"task_id": "t1"}], "mock_mode": "neutral"}),
        encoding="utf-8",
    )
    (work_dir / "stats.json").write_text(
        json.dumps({"gates": {"overall": "PASS"}}),
        encoding="utf-8",
    )

    module.cmd_report(argparse.Namespace())

    report = json.loads(module.REPORT_FILE.read_text(encoding="utf-8"))
    assert report["mock_mode"] == "neutral"
    assert (
        report["mock_mode_interpretation"]
        == "brief_effect_with_structurally_equivalent_edits"
    )


def test_report_marks_biased_mock_mode_as_fixture_bias(tmp_path: Path) -> None:
    module = load_ab_harness_module()
    work_dir = tmp_path / "ab_harness"
    work_dir.mkdir()
    module.WORK_DIR = work_dir
    module.OUTCOMES_FILE = work_dir / "outcomes.json"
    module.REPORT_FILE = work_dir / "report.json"
    module.OUTCOMES_FILE.write_text(
        json.dumps({"outcomes": [{"task_id": "t1"}], "mock_mode": "biased"}),
        encoding="utf-8",
    )
    (work_dir / "stats.json").write_text(
        json.dumps({"gates": {"overall": "PASS"}}),
        encoding="utf-8",
    )

    module.cmd_report(argparse.Namespace())

    report = json.loads(module.REPORT_FILE.read_text(encoding="utf-8"))
    assert report["mock_mode"] == "biased"
    assert report["mock_mode_interpretation"] == "structural_fixture_bias"
