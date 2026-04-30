"""MkDocs hook: inject version and release headline from project metadata.

Reads the canonical version from pyproject.toml and the latest changelog
summary from CHANGELOG.md so the announcement bar and templates always
reflect the current release — no manual edits needed.

Injected variables (available via {{ config.extra.<name> }} in templates):
  - version:          e.g. "2.6.0"
  - release_headline: e.g. "Signal-filtering for scan, cross-validation …"
  - release_date:     e.g. "2026-04-07"

Markdown replacement:
  - ``DRIFT_LATEST_TAG`` in .md files → ``v2.6.0`` (current tag)
"""

from __future__ import annotations

import re
from pathlib import Path

_cached_version: str | None = None


def on_config(config: dict) -> dict:
    """Populate config.extra with version metadata at build time."""
    global _cached_version
    root = Path(config["docs_dir"]).parent  # workspace root

    # --- version from pyproject.toml ---
    pyproject = root / "pyproject.toml"
    version = _extract_version(pyproject)
    if version:
        config["extra"]["version"] = version
        _cached_version = version

    # --- release headline + date from CHANGELOG.md ---
    changelog = root / "CHANGELOG.md"
    headline, date = _extract_latest_release(changelog)
    if headline:
        config["extra"]["release_headline"] = headline
    if date:
        config["extra"]["release_date"] = date

    return config


def on_page_markdown(markdown: str, **_kwargs: object) -> str:
    """Replace DRIFT_LATEST_TAG placeholder in markdown content."""
    if _cached_version and "DRIFT_LATEST_TAG" in markdown:
        return markdown.replace("DRIFT_LATEST_TAG", f"v{_cached_version}")
    return markdown


_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)
_RELEASE_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\]\s*-\s*(\d{4}-\d{2}-\d{2})")
_SHORT_RE = re.compile(r"^Short version:\s*(.+)", re.IGNORECASE)


def _extract_version(pyproject: Path) -> str | None:
    if not pyproject.is_file():
        return None
    m = _VERSION_RE.search(pyproject.read_text(encoding="utf-8"))
    return m.group(1) if m else None


def _extract_latest_release(changelog: Path) -> tuple[str | None, str | None]:
    """Return (headline, date) of the first non-Unreleased changelog entry."""
    if not changelog.is_file():
        return None, None
    lines = changelog.read_text(encoding="utf-8").splitlines()
    date: str | None = None
    for i, line in enumerate(lines):
        m = _RELEASE_RE.match(line)
        if m:
            date = m.group(2)
            # Look for "Short version:" line in the next few lines
            for j in range(i + 1, min(i + 6, len(lines))):
                sm = _SHORT_RE.match(lines[j])
                if sm:
                    return sm.group(1).strip(), date
            # No short version — fall back to version number
            return None, date
    return None, None
