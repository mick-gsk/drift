# ruff: noqa: E402, F401, F403
"""Compat stub: delegates to drift_output (ADR-102 Phase C)."""

from __future__ import annotations

import contextlib as _contextlib
import importlib as _importlib
import pkgutil as _pkgutil
import sys as _sys

import drift_output as _target

# Redirect __path__ so submodule imports resolve to drift_output.X
__path__ = _target.__path__  # type: ignore[assignment]

# Pre-register all submodules so that ``import drift.output.X`` and
# ``import drift_output.X`` return the same module object.  Without this,
# the ``__path__`` redirect causes Python to create a *second* module
# object for the same source file (``__name__ == "drift.output.X"``
# vs ``"drift_output.X"``), which breaks monkeypatch-based test isolation.
# Use try/except because some submodules have optional dependencies
# (e.g. tui_renderer requires ``textual``).
for _info in _pkgutil.iter_modules(_target.__path__):
    _full = f"{__name__}.{_info.name}"
    _src = f"drift_output.{_info.name}"
    if _full not in _sys.modules:
        with _contextlib.suppress(ImportError):
            _sys.modules[_full] = _importlib.import_module(_src)
    if _full in _sys.modules:
        globals().setdefault(_info.name, _sys.modules[_full])


def __getattr__(name: str) -> object:
    """Lazy-register submodule on first access to avoid circular imports."""
    _src = "drift_output." + name
    try:
        mod = _importlib.import_module(_src)
        _sys.modules[__name__ + "." + name] = mod
        return mod
    except ImportError:
        return getattr(_target, name)


from drift_output import *
