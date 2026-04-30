"""Tests for .github/workflows/drift-pr-reviewer.yml and .github/agents/reviewer.agent.md.

We cannot exercise the GitHub Actions runner from pytest, so we verify:

1. The workflow YAML parses and declares the required trigger/permission
   contract (pull_request on main + contents:read + pull-requests:write).
2. The workflow references the reviewer agent config, import-linter,
   and uses the idempotent comment marker.
3. The agent config exists and encodes the three required review rules
   (missing tests, module boundary violations, drift signal regressions).
4. CODEOWNERS covers the new agent-critical paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO = Path(__file__).resolve().parent.parent
WORKFLOW = REPO / ".github" / "workflows" / "drift-pr-reviewer.yml"
AGENT = REPO / ".github" / "agents" / "reviewer.agent.md"
CODEOWNERS = REPO / ".github" / "CODEOWNERS"


def _load_workflow() -> dict:
    assert WORKFLOW.exists(), f"missing {WORKFLOW}"
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


class TestWorkflowContract:
    def test_workflow_file_exists(self) -> None:
        assert WORKFLOW.exists(), f"missing workflow file: {WORKFLOW}"

    def test_trigger_is_pull_request_on_main(self) -> None:
        wf = _load_workflow()
        # PyYAML may turn the top-level ``on`` key into Python True (YAML 1.1
        # boolean); accept either form.
        on = wf.get("on") or wf.get(True)
        assert on is not None, "workflow missing 'on' trigger"
        assert "pull_request" in on
        pr_trigger = on["pull_request"]
        assert pr_trigger.get("branches") == ["main"], (
            "pull_request trigger must target 'main'"
        )

    def test_pull_request_types_include_synchronize(self) -> None:
        wf = _load_workflow()
        on = wf.get("on") or wf.get(True)
        pr_trigger = on["pull_request"]
        types = pr_trigger.get("types", [])
        assert "synchronize" in types, (
            "trigger must include 'synchronize' to re-run on push"
        )
        assert "opened" in types

    def test_permissions_write_pull_requests_read_contents(self) -> None:
        wf = _load_workflow()
        perms = wf["permissions"]
        assert perms["contents"] == "read"
        assert perms["pull-requests"] == "write", (
            "pull-requests: write is required to post the review comment"
        )

    def test_has_review_job(self) -> None:
        wf = _load_workflow()
        assert "review" in wf["jobs"], "expected a 'review' job"

    def test_review_job_skips_drafts(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        assert "draft" in raw, (
            "workflow must skip draft PRs to avoid noise on work-in-progress"
        )

    def test_concurrency_group_per_pr(self) -> None:
        wf = _load_workflow()
        concurrency = wf.get("concurrency", {})
        group = concurrency.get("group", "")
        assert "pull_request" in group or "pull" in group.lower(), (
            "concurrency group must be scoped per PR to avoid parallel duplicate runs"
        )

    def test_references_reviewer_agent(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        assert "reviewer.agent.md" in raw, (
            "workflow must reference the reviewer agent config"
        )

    def test_references_importlinter(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        assert "import-linter" in raw or "lint-imports" in raw, (
            "workflow must run import-linter for module boundary checks"
        )

    def test_idempotent_comment_marker_present(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        assert "drift-pr-reviewer" in raw, (
            "workflow must use a stable marker to upsert the PR comment"
        )

    def test_post_comment_step_uses_github_script(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        assert "actions/github-script" in raw, (
            "comment posting must use actions/github-script"
        )

    def test_drift_analyze_step_exits_zero(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        assert "--exit-zero" in raw, (
            "drift analyze must use --exit-zero so subsequent steps always run"
        )

    def test_missing_tests_step_present(self) -> None:
        raw = WORKFLOW.read_text(encoding="utf-8")
        assert "missing" in raw.lower() and "test" in raw.lower(), (
            "workflow must include a missing-test detection step"
        )


class TestAgentConfig:
    def test_agent_file_exists(self) -> None:
        assert AGENT.exists(), f"missing reviewer agent config: {AGENT}"

    def test_agent_has_description_frontmatter(self) -> None:
        text = AGENT.read_text(encoding="utf-8")
        assert text.startswith("---"), "agent file must start with YAML frontmatter"
        assert "description" in text[:300], (
            "frontmatter must contain a 'description' field for agent discovery"
        )

    def test_agent_description_contains_trigger_keywords(self) -> None:
        text = AGENT.read_text(encoding="utf-8")
        # Discovery surface: description must contain recognizable keywords
        assert "PR review" in text or "reviewer" in text.lower()
        assert "importlinter" in text or "import-linter" in text

    def test_agent_encodes_missing_tests_rule(self) -> None:
        text = AGENT.read_text(encoding="utf-8")
        assert "Missing" in text and "test" in text.lower(), (
            "agent must encode the missing-tests recurring pattern"
        )

    def test_agent_encodes_importlinter_rule(self) -> None:
        text = AGENT.read_text(encoding="utf-8")
        # Must reference the four configured contracts
        assert "ingestion-no-output" in text or "ingestion" in text
        assert "models-independence" in text or "models" in text
        assert "signals-no-output" in text or "signals" in text
        assert "scoring-no-output" in text or "scoring" in text

    def test_agent_encodes_drift_signals_rule(self) -> None:
        text = AGENT.read_text(encoding="utf-8")
        assert "PATTERN_FRAGMENTATION" in text or "drift signal" in text.lower(), (
            "agent must reference drift signals used for regression detection"
        )

    def test_agent_declares_report_only_constraint(self) -> None:
        text = AGENT.read_text(encoding="utf-8")
        assert "report-only" in text.lower() or "Report-only" in text, (
            "agent must explicitly state it is report-only (no blocking)"
        )

    def test_agent_declares_idempotent_comment(self) -> None:
        text = AGENT.read_text(encoding="utf-8")
        assert "drift-pr-reviewer" in text or "idempotent" in text.lower(), (
            "agent must specify the idempotent comment marker or strategy"
        )

    def test_agent_references_importlinter_file(self) -> None:
        text = AGENT.read_text(encoding="utf-8")
        assert ".importlinter" in text, (
            "agent must reference .importlinter as the authoritative contract source"
        )

    def test_agent_references_review_checklist(self) -> None:
        text = AGENT.read_text(encoding="utf-8")
        assert "review-checkliste.md" in text, (
            "agent must reference the shared review checklist"
        )

    def test_agent_references_workflow(self) -> None:
        text = AGENT.read_text(encoding="utf-8")
        assert "drift-pr-reviewer.yml" in text, (
            "agent must reference the activating workflow"
        )


class TestCodeownersCoverage:
    @pytest.mark.parametrize(
        "path",
        [
            ".github/agents/reviewer.agent.md",
            ".github/workflows/drift-pr-reviewer.yml",
        ],
    )
    def test_reviewer_path_has_owner(self, path: str) -> None:
        content = CODEOWNERS.read_text(encoding="utf-8")
        assert path in content, (
            f"CODEOWNERS missing reviewer path: {path}"
        )
