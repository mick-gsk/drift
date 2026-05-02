# ruff: noqa: F401, F403
"""Compat stub: delegates to drift_cli.commands (ADR-102 Phase C)."""

from __future__ import annotations

import importlib as _importlib
import sys as _sys

import drift_cli.commands as _target

# Redirect __path__ so `from drift.commands.X import Y` finds drift_cli.commands.X
__path__ = _target.__path__  # type: ignore[assignment]

# Explicit re-exports that mypy needs to see as typed symbols
from drift_cli.commands import make_console as make_console


def __getattr__(name: str) -> object:
    """Lazy-load submodule attributes from drift_cli.commands."""
    try:
        mod = _importlib.import_module(f"drift_cli.commands.{name}")
        _sys.modules[f"{__name__}.{name}"] = mod
        return mod
    except ImportError:
        return getattr(_target, name)
