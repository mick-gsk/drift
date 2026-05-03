"""Contract tests for Copilot coding agent issue brief workflow."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
TEMPLATE = REPO / ".github" / "ISSUE_TEMPLATE" / "copilot_agent_task.yml"
WORKFLOW = REPO / ".github" / "workflows" / "copilot-agent-issue-brief-check.yml"

REQUIRED_LABELS = (
    "Goal",
    "Scope",
    "Acceptance criteria",
    "Verification",
    "Constraints and guardrails",
    "Non-goals",
)

SECTION_PATTERNS = {
    "Goal": re.compile(r"^#{2,3}\s*Goal\b", re.IGNORECASE | re.MULTILINE),
    "Scope": re.compile(r"^#{2,3}\s*Scope\b", re.IGNORECASE | re.MULTILINE),
    "Acceptance criteria": re.compile(
        r"^#{2,3}\s*Acceptance\s+Criteria\b", re.IGNORECASE | re.MULTILINE
    ),
    "Verification": re.compile(r"^#{2,3}\s*Verification\b", re.IGNORECASE | re.MULTILINE),
    "Constraints and guardrails": re.compile(
        r"^#{2,3}\s*(Constraints|Constraints and guardrails)\b",
        re.IGNORECASE | re.MULTILINE,
    ),
    "Non-goals": re.compile(r"^#{2,3}\s*Non-goals\b", re.IGNORECASE | re.MULTILINE),
}


def _template() -> dict:
    return yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))


def _missing_sections(issue_body: str) -> list[str]:
    missing: list[str] = []
    for label, pattern in SECTION_PATTERNS.items():
        if not pattern.search(issue_body):
            missing.append(label)
    return missing


class TestCopilotAgentIssueTemplate:
    def test_template_exists_and_has_copilot_label(self) -> None:
        assert TEMPLATE.exists()
        data = _template()
        labels = set(data.get("labels", []))
        assert "copilot-agent" in labels

    def test_template_contains_required_brief_fields(self) -> None:
        data = _template()
        labels = [item.get("attributes", {}).get("label") for item in data.get("body", [])]
        for required in REQUIRED_LABELS:
            assert required in labels


class TestCopilotAgentIssueWorkflow:
    def test_workflow_exists_and_is_issue_triggered(self) -> None:
        assert WORKFLOW.exists()
        data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
        on_block = data.get("on")
        if on_block is None:
            # PyYAML may coerce the key 'on' to boolean True (YAML 1.1 behavior).
            on_block = data.get(True, {})
        issues = on_block.get("issues", {})
        issue_types = set(issues.get("types", []))
        expected = {"opened", "edited", "reopened", "labeled", "unlabeled"}
        assert expected.issubset(issue_types)

    def test_workflow_references_copilot_agent_labels(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        assert "copilot-agent" in raw
        assert "needs-agent-brief" in raw

    def test_section_detection_contract_matches_template_style(self) -> None:
        complete = """
### Goal
Add validation for unknown config keys.

### Scope
Only config parser and config tests.

### Acceptance Criteria
- [ ] Unknown keys produce clear user-facing error

### Verification
make test-fast

### Constraints and guardrails
- Keep API stable

### Non-goals
- No dependency upgrade
"""
        assert _missing_sections(complete) == []

    def test_section_detection_flags_missing_brief_sections(self) -> None:
        incomplete = """
### Goal
Stabilize issue brief checker.

### Scope
Workflow file only.

### Verification
python -m pytest tests/test_copilot_agent_issue_brief_contract.py -q
"""
        assert _missing_sections(incomplete) == [
            "Acceptance criteria",
            "Constraints and guardrails",
            "Non-goals",
        ]
