# ruff: noqa: F401, F403
import importlib as _il
import sys as _sys

_t = _il.import_module('drift_mcp.pr_loop')
_sys.modules[__name__] = _t
for _k, _v in list(_sys.modules.items()):
    if _k.startswith('drift_mcp.pr_loop.'):
        _sys.modules.setdefault(__name__ + _k[17:], _v)
