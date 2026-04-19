"""Auto-save helper: persist last successful scan snapshot for ``drift diff --auto``."""

from __future__ import annotations

import logging
from pathlib import Path

LAST_SCAN_FILENAME = "last_scan.json"
LOGGER = logging.getLogger(__name__)


def get_last_scan_path(repo_path: Path, cache_dir: str) -> Path:
    """Return the path to the last-scan snapshot file."""
    return repo_path / cache_dir / LAST_SCAN_FILENAME


def analysis_to_json(analysis: object, **kwargs) -> str:  # noqa: ANN001
    """Thin wrapper so tests can monkeypatch at a stable import location."""
    from drift.output.json_output import analysis_to_json as _impl

    return _impl(analysis, **kwargs)  # type: ignore[arg-type]


def save_last_scan(analysis: object, repo_path: Path, cache_dir: str) -> None:
    """Persist a minimal analyze-JSON snapshot used by ``drift diff --auto``.

    Silently skips on any error so it never disrupts the main ``analyze`` command.
    """
    try:
        dest = get_last_scan_path(repo_path, cache_dir)
        dest.parent.mkdir(parents=True, exist_ok=True)
        json_text = analysis_to_json(analysis, compact=False, response_detail="concise")
        dest.write_text(json_text, encoding="utf-8")
    except Exception:
        LOGGER.debug("Failed to save last_scan.json", exc_info=True)
