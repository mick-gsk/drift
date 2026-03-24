"""Drift — Detect architectural erosion from AI-generated code."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


def _resolve_version() -> str:
    """Resolve installed package version for CLI/output metadata."""
    for package_name in ("drift-analyzer", "drift"):
        try:
            return version(package_name)
        except PackageNotFoundError:
            continue
    return "0.0.0"


__version__ = _resolve_version()
