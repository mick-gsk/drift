# ruff: noqa: F401, F403, E501
import importlib as _importlib
import sys as _sys

# Explicit re-exports for mypy (sys.modules aliasing is invisible to static analysis)
from drift_engine.patch_writer import PatchResult as PatchResult
from drift_engine.patch_writer import PatchResultStatus as PatchResultStatus
from drift_engine.patch_writer import PatchWriter as PatchWriter
from drift_engine.patch_writer import get_writer as get_writer
from drift_engine.patch_writer import supported_edit_kinds as supported_edit_kinds

_target = _importlib.import_module("drift_engine.patch_writer")
_sys.modules[__name__] = _target
for _k, _v in list(_sys.modules.items()):
    if _k.startswith("drift_engine.patch_writer."):
        _sys.modules.setdefault(__name__ + _k[25:], _v)
