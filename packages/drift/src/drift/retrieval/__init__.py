# ruff: noqa: E402, F401, F403
"""Compat stub: delegates to drift_engine.retrieval (ADR-102 Phase C)."""

from __future__ import annotations

import importlib as _importlib
import sys as _sys

import drift_engine.retrieval as _target

# Redirect __path__ so submodule imports resolve to drift_engine.retrieval.X
__path__ = _target.__path__  # type: ignore[assignment]


def __getattr__(name: str) -> object:
    """Lazy-register submodule on first access to avoid circular imports."""
    _src = "drift_engine.retrieval." + name
    try:
        mod = _importlib.import_module(_src)
        _sys.modules[__name__ + "." + name] = mod
        return mod
    except ImportError:
        return getattr(_target, name)


from drift_engine.retrieval import *
