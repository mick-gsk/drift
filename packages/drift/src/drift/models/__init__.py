# ruff: noqa: E402, F401, F403
"""Compat stub: delegates to drift_sdk.models (ADR-102 Phase C)."""

from __future__ import annotations

import importlib as _importlib
import pkgutil as _pkgutil
import sys as _sys

import drift_sdk.models as _target

# Redirect __path__ so submodule imports resolve to drift_sdk.models.X
__path__ = _target.__path__  # type: ignore[assignment]

# Pre-register all submodules to ensure class-identity stays consistent
for _info in _pkgutil.iter_modules(_target.__path__):
    _full = f"{__name__}.{_info.name}"
    _src = f"drift_sdk.models.{_info.name}"
    if _full not in _sys.modules:
        _sys.modules[_full] = _importlib.import_module(_src)
    # Also set as attribute so monkeypatch string-form works
    globals().setdefault(_info.name, _sys.modules[_full])

from drift_sdk.models import *
