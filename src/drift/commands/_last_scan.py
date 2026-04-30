"""Auto-save helper: persist last successful scan snapshot for ``drift diff --auto``."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

LAST_SCAN_FILENAME = "last_scan.json"
LOGGER = logging.getLogger(__name__)


def get_last_scan_path(repo_path: Path, cache_dir: str) -> Path:
    """Return the path to the last-scan snapshot file."""
    return repo_path / cache_dir / LAST_SCAN_FILENAME


def _get_last_scan_path_with_cfg(repo_path: Path, cache_dir: str, cfg: Any) -> Path:
    """Return the last-scan path, honouring cfg.resolve_artifact_path when available."""
    if cfg is not None and hasattr(cfg, "resolve_artifact_path"):
        return Path(cfg.resolve_artifact_path(repo_path, cache_dir)) / LAST_SCAN_FILENAME
    return get_last_scan_path(repo_path, cache_dir)


def analysis_to_json(analysis: object, **kwargs) -> str:  # noqa: ANN001
    """Thin wrapper so tests can monkeypatch at a stable import location."""
    from drift.output.json_output import analysis_to_json as _impl

    return _impl(analysis, **kwargs)  # type: ignore[arg-type]


def save_last_scan(
    analysis: object, repo_path: Path, cache_dir: str, cfg: Any = None
) -> None:
    """Persist a minimal analyze-JSON snapshot used by ``drift diff --auto``.

    Silently skips on any error so it never disrupts the main ``analyze`` command.
    When *cfg* is provided and has ``resolve_artifact_path``, the snapshot is
    written to the configured ``output_root`` rather than inside the repo.
    """
    try:
        dest = _get_last_scan_path_with_cfg(repo_path, cache_dir, cfg)

        dest.parent.mkdir(parents=True, exist_ok=True)
        json_text = analysis_to_json(analysis, compact=False, response_detail="concise")
        dest.write_text(json_text, encoding="utf-8")
    except Exception:
        LOGGER.debug("Failed to save last_scan.json", exc_info=True)
