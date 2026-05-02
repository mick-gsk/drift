# ruff: noqa: E402, F401, F403
"""Compat stub: delegates to drift_engine.intent (ADR-102 Phase C)."""

from __future__ import annotations

import importlib as _importlib
import pkgutil as _pkgutil
import sys as _sys

import drift_engine.intent as _target

# Redirect __path__ so submodule imports resolve to drift_engine.intent.X
__path__ = _target.__path__  # type: ignore[assignment]

# Pre-register submodules to keep module identity stable.
for _info in _pkgutil.iter_modules(_target.__path__):
    _full = f"{__name__}.{_info.name}"
    if _full not in _sys.modules:
        _sys.modules[_full] = _importlib.import_module(
            f"drift_engine.intent.{_info.name}"
        )


def __getattr__(name: str) -> object:
    """Lazy-register submodule on first access to avoid circular imports."""
    _src = "drift_engine.intent." + name
    try:
        mod = _importlib.import_module(_src)
        _sys.modules[__name__ + "." + name] = mod
        return mod
    except ImportError:
        return getattr(_target, name)


from drift_engine.intent import *
