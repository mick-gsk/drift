from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_enterprise_governance_assets_exist() -> None:
    required_paths = [
        ".devcontainer/devcontainer.json",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/ISSUE_TEMPLATE/false_positive.yml",
        ".github/DISCUSSION_TEMPLATE/questions.yml",
        ".github/DISCUSSION_TEMPLATE/ideas.yml",
        ".pre-commit-config.yaml",
        "CITATION.cff",
    ]

    missing = [path for path in required_paths if not (REPO_ROOT / path).exists()]
    assert missing == []
