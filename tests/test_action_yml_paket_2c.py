"""Tests for action.yml Paket 2C / ADR-095 contract."""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO = Path(__file__).resolve().parent.parent
ACTION = REPO / "action.yml"
ADR = REPO / "docs" / "decisions" / "ADR-095-auto-issue-filing.md"
TEMPLATE = REPO / ".github" / "ISSUE_TEMPLATE" / "drift-block.yml"


def _action() -> dict:
    return yaml.safe_load(ACTION.read_text(encoding="utf-8"))


class TestActionInputs:
    def test_create_issue_input_exists_and_defaults_false(self) -> None:
        data = _action()
        assert "create-issue" in data["inputs"]
        assert data["inputs"]["create-issue"]["default"] == "false"

    def test_issue_labels_input_exists_with_default(self) -> None:
        data = _action()
        assert "issue-labels" in data["inputs"]
        assert "drift" in data["inputs"]["issue-labels"]["default"]


class TestActionStep:
    def test_auto_file_step_present_and_guarded(self) -> None:
        raw = ACTION.read_text(encoding="utf-8")
        assert "Auto-file BLOCK drift findings as issues" in raw
        assert "inputs.create-issue == 'true'" in raw
        assert "gh_issue_dedup.py" in raw

    def test_report_file_output_is_wired(self) -> None:
        raw = ACTION.read_text(encoding="utf-8")
        # drift-run step must emit report-file so the dedup step can find the JSON.
        assert "report-file=" in raw


class TestAdr095AndTemplate:
    def test_adr_exists_and_proposed(self) -> None:
        assert ADR.exists()
        text = ADR.read_text(encoding="utf-8")
        assert "ADR-095" in text
        assert "proposed" in text.lower()

    def test_issue_template_exists_with_dedup_reference(self) -> None:
        assert TEMPLATE.exists()
        text = TEMPLATE.read_text(encoding="utf-8")
        assert "drift-finding-id" in text
