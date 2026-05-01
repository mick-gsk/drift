# ruff: noqa: F401, F403, E501
import importlib as _importlib
import sys as _sys

_target = _importlib.import_module("drift_engine.lang")
_sys.modules[__name__] = _target
for _k, _v in list(_sys.modules.items()):
    if _k.startswith("drift_engine.lang."):
        _sys.modules.setdefault(__name__ + _k[17:], _v)
