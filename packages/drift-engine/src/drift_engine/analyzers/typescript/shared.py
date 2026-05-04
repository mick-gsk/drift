"""Shared helpers for TypeScript analyzers."""

from __future__ import annotations

from pathlib import Path

_IGNORED_TS_PATH_PARTS = {
    "node_modules",
    "__pycache__",
    "venv",
    ".venv",
    ".git",
    "dist",
    "build",
}


def iter_ts_sources(repo_path: Path) -> list[Path]:
    """Return repository-relative .ts/.tsx source files sorted by POSIX path."""

    def _is_ignored(path: Path) -> bool:
        return any(part in _IGNORED_TS_PATH_PARTS for part in path.parts)

    files = [
        path.relative_to(repo_path)
        for path in repo_path.rglob("*.ts")
        if path.is_file() and not _is_ignored(path)
    ]
    files.extend(
        path.relative_to(repo_path)
        for path in repo_path.rglob("*.tsx")
        if path.is_file() and not _is_ignored(path)
    )
    return sorted(set(files), key=lambda p: p.as_posix())
