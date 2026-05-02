"""Shared utilities for signal implementations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from drift_engine.ingestion.test_detection import is_test_file as _is_test_file

_TS_LANGUAGES: frozenset[str] = frozenset(
    {"typescript", "tsx", "javascript", "jsx"},
)

_SUPPORTED_LANGUAGES: frozenset[str] = frozenset({"python"}) | _TS_LANGUAGES

_LIBRARY_ROOT_DIRS: frozenset[str] = frozenset({"src", "lib", "packages"})
_APPLICATION_ROOT_DIRS: frozenset[str] = frozenset(
    {"app", "apps", "backend", "frontend", "service", "services", "server", "web"}
)


def is_test_file(file_path: Path) -> bool:
    """Return True if *file_path* looks like a test file (by name / path).

    Covers Python, TypeScript / JavaScript and common JS test directories.
    """
    return _is_test_file(file_path)


def is_library_finding_path(file_path: Path | None) -> bool:
    """Return True when *file_path* matches common library source layouts."""
    if file_path is None:
        return False
    parts = file_path.as_posix().lower().split("/")
    if not parts:
        return False
    if any(part in _LIBRARY_ROOT_DIRS for part in parts):
        return True
    # Monorepo layout: packages/<pkg>/(src|lib)/...
    return any(
        parts[idx] == "packages" and idx + 2 < len(parts) and parts[idx + 2] in {"src", "lib"}
        for idx in range(len(parts))
    )


def is_likely_library_repo(parse_results: list[Any]) -> bool:
    """Heuristic repository profile detection for library-style layouts.

    Conservative by design: requires at least one library-style root and no
    strong application root markers.
    """
    path_tokens: set[str] = set()
    for pr in parse_results:
        file_path = getattr(pr, "file_path", None)
        if not isinstance(file_path, Path):
            continue
        if is_test_file(file_path):
            continue
        parts = file_path.as_posix().lower().split("/")
        path_tokens.update(part for part in parts if part)

    has_library_layout = any(token in _LIBRARY_ROOT_DIRS for token in path_tokens)
    has_application_layout = any(token in _APPLICATION_ROOT_DIRS for token in path_tokens)
    return has_library_layout and not has_application_layout


# ---------------------------------------------------------------------------
# Tree-sitter helpers live in _ts_support to avoid pulling the unstable
# ts_parser dependency into this high-fan-in utility module.
# Signals should import ts_parse_source / ts_walk / ts_node_text from
# drift.signals._ts_support directly.
# ---------------------------------------------------------------------------
