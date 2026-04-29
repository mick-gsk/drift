"""Fetch repository stats from the GitHub REST API.

Returns stars, forks, open issue count, and open bug count (issues with a
configurable label).  Designed as a library module imported by
``collect_kpi_snapshot.py``; can also be run as a standalone script.

Usage (standalone):
    python scripts/fetch_github_stats.py --repo mick-gsk/drift

Authentication:
    Set the ``GITHUB_TOKEN`` environment variable for higher rate limits
    (5 000 req/h authenticated vs. 60 req/h anonymous).  The token is
    optional — unauthenticated access is sufficient for daily CI snapshots.
"""

from __future__ import annotations

import argparse
import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

_API_BASE = "https://api.github.com"
_DEFAULT_TIMEOUT = 15
_BUG_LABEL_DEFAULT = "bug"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _make_request(url: str, token: str | None, timeout: int) -> Any:
    """Return parsed JSON from *url*, raising on HTTP/network errors."""
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "drift-kpi-snapshot/1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout) as resp:  # noqa: S310  # nosec B310
        return json.loads(resp.read().decode("utf-8"))


def _count_via_search(
    repo: str,
    label: str,
    token: str | None,
    timeout: int,
) -> int | None:
    """Count open issues with *label* using the issues list endpoint.

    Returns the total count inferred from pagination headers, or ``None``
    on error.  We request ``per_page=1`` and read the ``Link`` header to
    find the last page number (= total count for single-label queries).
    """
    url = (
        f"{_API_BASE}/repos/{repo}/issues"
        f"?state=open&labels={quote_plus(label)}&per_page=1&page=1"
    )
    headers: dict[str, str] = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "drift-kpi-snapshot/1",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    try:
        with urlopen(request, timeout=timeout) as resp:  # noqa: S310  # nosec B310
            link_header = resp.getheader("Link") or ""
            body = json.loads(resp.read().decode("utf-8"))
        # If there's no Link header, the full result fits in one page
        if not link_header:
            return len(body)
        # Parse last page number from Link header
        # Example: <https://...?page=7>; rel="last"
        for part in link_header.split(","):
            if 'rel="last"' in part:
                import re
                match = re.search(r"[?&]page=(\d+)", part)
                if match:
                    return int(match.group(1))
        return len(body)
    except (HTTPError, URLError, OSError):
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def fetch_github_stats(
    repo: str = "mick-gsk/drift",
    *,
    token: str | None = None,
    bug_label: str = _BUG_LABEL_DEFAULT,
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict[str, int | None] | None:
    """Fetch GitHub repository stats.

    Args:
        repo: ``owner/name`` repository slug.
        token: GitHub personal access token.  Falls back to the
            ``GITHUB_TOKEN`` environment variable if ``None``.
        bug_label: Issue label used to count open bugs (default ``"bug"``).
        timeout: HTTP request timeout in seconds.

    Returns:
        A dict with keys ``stars``, ``forks``, ``open_issues``,
        ``open_bugs``.  Values are ``int`` or ``None`` when unavailable.
        Returns ``None`` when the repository endpoint itself is unreachable.
    """
    resolved_token = token if token is not None else os.environ.get("GITHUB_TOKEN")

    # --- Repository metadata ---
    try:
        repo_data = _make_request(
            f"{_API_BASE}/repos/{repo}",
            resolved_token,
            timeout,
        )
    except (HTTPError, URLError, OSError):
        return None

    stars: int | None = repo_data.get("stargazers_count")
    forks: int | None = repo_data.get("forks_count")

    # Use Search API to get accurate issue-only count (open_issues_count includes PRs).
    open_issues: int | None = None
    try:
        search_data = _make_request(
            f"{_API_BASE}/search/issues?q={quote_plus(f'is:issue is:open repo:{repo}')}&per_page=1",
            resolved_token,
            timeout,
        )
        open_issues = search_data.get("total_count")
    except (HTTPError, URLError, OSError):
        # Fall back to the repo field (includes PRs) on error
        raw = repo_data.get("open_issues_count")
        open_issues = int(raw) if raw is not None else None

    # --- Bug count ---
    open_bugs = _count_via_search(repo, bug_label, resolved_token, timeout)

    return {
        "stars": int(stars) if stars is not None else None,
        "forks": int(forks) if forks is not None else None,
        "open_issues": int(open_issues) if open_issues is not None else None,
        "open_bugs": open_bugs,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch GitHub repository stats")
    parser.add_argument(
        "--repo",
        default="mick-gsk/drift",
        help="owner/name slug (default: mick-gsk/drift)",
    )
    parser.add_argument(
        "--bug-label",
        default=_BUG_LABEL_DEFAULT,
        help=f"Issue label for open-bug count (default: {_BUG_LABEL_DEFAULT!r})",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=_DEFAULT_TIMEOUT,
        help="HTTP timeout in seconds",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = fetch_github_stats(
        args.repo,
        bug_label=args.bug_label,
        timeout=args.timeout,
    )
    if result is None:
        raise SystemExit(f"Could not reach GitHub API for repo '{args.repo}'")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
