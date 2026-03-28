from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_module():
    module_path = Path(__file__).resolve().parent.parent / "scripts" / "fetch_github_usage.py"
    spec = importlib.util.spec_from_file_location("fetch_github_usage", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_build_queries_contains_expected_filenames() -> None:
    module = _load_module()

    queries = module._build_queries("drift-analyzer")

    assert len(queries) >= 3
    assert any("filename:pyproject.toml" in q for q in queries)
    assert any("filename:requirements.txt" in q for q in queries)


def test_extract_repo_activity_deduplicates_by_repo_and_skips_archived() -> None:
    module = _load_module()

    items = [
        {
            "repository": {
                "full_name": "acme/project-a",
                "pushed_at": "2026-03-01T10:00:00Z",
                "archived": False,
            }
        },
        {
            "repository": {
                "full_name": "acme/project-a",
                "pushed_at": "2026-03-04T10:00:00Z",
                "archived": False,
            }
        },
        {
            "repository": {
                "full_name": "acme/project-b",
                "pushed_at": "2026-03-03T10:00:00Z",
                "archived": True,
            }
        },
    ]

    activity = module._extract_repo_activity(items)

    assert activity == {"acme/project-a": "2026-03-04T10:00:00Z"}


def test_usage_rows_are_sorted() -> None:
    module = _load_module()

    rows = module._usage_rows(
        {
            "zeta/repo": "2026-03-01T00:00:00Z",
            "alpha/repo": "2026-03-02T00:00:00Z",
        },
        default_version="unknown",
    )

    assert rows[0]["project_id"] == "alpha/repo"
    assert rows[1]["project_id"] == "zeta/repo"
    assert rows[0]["version"] == "unknown"


def test_extract_repo_names_deduplicates() -> None:
    module = _load_module()

    names = module._extract_repo_names(
        [
            {"repository": {"full_name": "acme/a"}},
            {"repository": {"full_name": "acme/a"}},
            {"repository": {"full_name": "acme/b"}},
        ]
    )

    assert names == ["acme/a", "acme/b"]


def test_resolve_repo_activity_via_repo_api_skips_archived(monkeypatch) -> None:
    module = _load_module()

    def _fake_fetch(repo_full_name: str, token: str | None, timeout: int):
        if repo_full_name == "acme/archived":
            return ("2026-03-01T00:00:00Z", True)
        return ("2026-03-02T00:00:00Z", False)

    monkeypatch.setattr(module, "_fetch_repo_activity", _fake_fetch)

    activity = module._resolve_repo_activity_via_repo_api(
        repo_full_names=["acme/live", "acme/archived"],
        token=None,
        timeout=30,
        include_archived=False,
    )

    assert activity == {"acme/live": "2026-03-02T00:00:00Z"}
