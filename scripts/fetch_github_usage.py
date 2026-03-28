"""Derive monthly project usage events from public GitHub dependency declarations.

This script scans public repositories via the GitHub Code Search API for files
that declare a dependency on a package. Each matched repository contributes one
usage event keyed by repository full name and latest push timestamp.

Usage:
  python scripts/fetch_github_usage.py \
    --package drift-analyzer \
    --output benchmark_results/package_kpis/github_usage_events.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

SEARCH_FILENAMES: tuple[str, ...] = (
    "pyproject.toml",
    "requirements.txt",
    "requirements-dev.txt",
    "setup.py",
    "Pipfile",
    "poetry.lock",
)


def _build_queries(package: str) -> list[str]:
    return [f'"{package}" in:file filename:{name}' for name in SEARCH_FILENAMES]


def _github_get_json(url: str, token: str | None, timeout: int) -> dict[str, object]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "drift-package-kpis/1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


def _search_code(
    query: str,
    token: str | None,
    timeout: int,
    per_page: int,
    max_pages: int,
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for page in range(1, max_pages + 1):
        encoded_query = quote_plus(query)
        url = (
            "https://api.github.com/search/code"
            f"?q={encoded_query}&per_page={per_page}&page={page}"
        )
        data = _github_get_json(url, token=token, timeout=timeout)
        page_items = data.get("items", [])
        if not isinstance(page_items, list) or not page_items:
            break

        items.extend(item for item in page_items if isinstance(item, dict))
        if len(page_items) < per_page:
            break

    return items


def _extract_repo_activity(
    items: list[dict[str, object]], include_archived: bool = False
) -> dict[str, str]:
    activity: dict[str, str] = {}
    for item in items:
        repo_obj = item.get("repository")
        if not isinstance(repo_obj, dict):
            continue

        full_name = str(repo_obj.get("full_name", "")).strip()
        pushed_at = str(repo_obj.get("pushed_at", "")).strip()
        archived = bool(repo_obj.get("archived", False))

        if not full_name or not pushed_at:
            continue
        if archived and not include_archived:
            continue

        previous = activity.get(full_name)
        if previous is None or pushed_at > previous:
            activity[full_name] = pushed_at

    return activity


def _extract_repo_names(items: list[dict[str, object]]) -> list[str]:
    names: set[str] = set()
    for item in items:
        repo_obj = item.get("repository")
        if not isinstance(repo_obj, dict):
            continue
        full_name = str(repo_obj.get("full_name", "")).strip()
        if full_name:
            names.add(full_name)
    return sorted(names)


def _fetch_repo_activity(
    repo_full_name: str,
    token: str | None,
    timeout: int,
) -> tuple[str | None, bool]:
    data = _github_get_json(
        f"https://api.github.com/repos/{repo_full_name}",
        token=token,
        timeout=timeout,
    )
    pushed_at = data.get("pushed_at")
    archived = bool(data.get("archived", False))
    return (str(pushed_at).strip() if pushed_at else None, archived)


def _resolve_repo_activity_via_repo_api(
    repo_full_names: list[str],
    token: str | None,
    timeout: int,
    include_archived: bool,
) -> dict[str, str]:
    activity: dict[str, str] = {}
    for repo_full_name in repo_full_names:
        try:
            pushed_at, archived = _fetch_repo_activity(
                repo_full_name=repo_full_name,
                token=token,
                timeout=timeout,
            )
        except HTTPError as exc:
            if exc.code in {403, 404}:
                continue
            raise

        if not pushed_at:
            continue
        if archived and not include_archived:
            continue
        activity[repo_full_name] = pushed_at
    return activity


def _usage_rows(activity_by_repo: dict[str, str], default_version: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for project_id in sorted(activity_by_repo):
        rows.append(
            {
                "timestamp": activity_by_repo[project_id],
                "project_id": project_id,
                "version": default_version,
            }
        )
    return rows


def _write_usage_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["timestamp", "project_id", "version"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Derive usage events from public GitHub dependency declarations"
    )
    parser.add_argument("--package", required=True, help="Package name to search")
    parser.add_argument(
        "--token",
        default=None,
        help="GitHub token (default: env GITHUB_TOKEN)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout seconds (default: 30)",
    )
    parser.add_argument(
        "--per-page",
        type=int,
        default=100,
        help="Search API page size (default: 100)",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="Max pages per query (default: 5)",
    )
    parser.add_argument(
        "--default-version",
        default="unknown",
        help="Version value used in usage events (default: unknown)",
    )
    parser.add_argument(
        "--include-archived",
        action="store_true",
        default=False,
        help="Include archived repositories",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmark_results/package_kpis/github_usage_events.csv"),
        help="Output CSV path",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    token = args.token or os.getenv("GITHUB_TOKEN")

    all_items: list[dict[str, object]] = []
    for query in _build_queries(args.package):
        try:
            items = _search_code(
                query=query,
                token=token,
                timeout=args.timeout,
                per_page=args.per_page,
                max_pages=args.max_pages,
            )
        except HTTPError as exc:
            if exc.code == 403:
                raise SystemExit(
                    "GitHub API rate limit hit or forbidden. Provide --token or set GITHUB_TOKEN."
                ) from exc
            raise SystemExit(f"GitHub API HTTP error: {exc.code}") from exc
        except URLError as exc:
            raise SystemExit(f"GitHub API network error: {exc.reason}") from exc

        all_items.extend(items)

    repo_names = _extract_repo_names(all_items)
    activity = _resolve_repo_activity_via_repo_api(
        repo_full_names=repo_names,
        token=token,
        timeout=args.timeout,
        include_archived=args.include_archived,
    )
    rows = _usage_rows(activity, default_version=args.default_version)
    _write_usage_csv(args.output, rows)

    print(
        f"Derived {len(rows)} unique projects from {len(all_items)} search hits."
    )
    print(f"Wrote usage events to {args.output}")
    print(f"Generated at {datetime.now(UTC).isoformat()}")


if __name__ == "__main__":
    main()
