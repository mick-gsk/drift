"""Meta compatibility package for ADR-100 phase 6a.

This package keeps ``drift.*`` import paths stable while capability modules
are moved into dedicated workspace packages.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def _resolve_version() -> str:
    """Resolve installed package version for CLI/output metadata."""
    for package_name in ("drift-analyzer", "drift-analyzer-meta", "drift"):
        try:
            return version(package_name)
        except PackageNotFoundError:
            continue
    return "0.0.0"


# During workspace development, keep legacy ``src/drift`` on package search path
# so all existing re-export stubs remain importable without duplicating modules.
_workspace_src = Path(__file__).resolve().parents[4] / "src" / "drift"
if _workspace_src.exists():
    path_entry = str(_workspace_src)
    if path_entry not in __path__:
        __path__.append(path_entry)


__version__ = _resolve_version()
