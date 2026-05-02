# ruff: noqa: E402, F401, F403
"""Compat stub: delegates to drift_engine.signals (ADR-102 Phase C)."""

from __future__ import annotations

import importlib as _importlib
import pkgutil as _pkgutil
import sys as _sys

import drift_engine.signals as _target

# Redirect __path__ so submodule imports resolve to drift_engine.signals.X
__path__ = _target.__path__  # type: ignore[assignment]

# Pre-register all submodules to ensure class-identity stays consistent
for _info in _pkgutil.iter_modules(_target.__path__):
    _full = f"{__name__}.{_info.name}"
    _src = f"drift_engine.signals.{_info.name}"
    if _full not in _sys.modules:
        _sys.modules[_full] = _importlib.import_module(_src)
    # Also set as attribute so monkeypatch string-form works
    globals().setdefault(_info.name, _sys.modules[_full])


def __getattr__(name: str) -> object:
    """Fallback: forward attribute lookups to the canonical module."""
    _src = "drift_engine.signals." + name
    try:
        mod = _importlib.import_module(_src)
        _sys.modules[__name__ + "." + name] = mod
        globals()[name] = mod
        return mod
    except ImportError:
        return getattr(_target, name)

from drift_engine.signals import *
