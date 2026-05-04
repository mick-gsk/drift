"""Re-export stub -- canonical implementation lives in drift_engine.fix_intent."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_engine.fix_intent import *

# Explicit re-exports for mypy (sys.modules aliasing is invisible to static analysis)
from drift_engine.fix_intent import (
    _EDIT_KIND_FOR_SIGNAL as _EDIT_KIND_FOR_SIGNAL,
)
from drift_engine.fix_intent import (
    _refine_edit_kind as _refine_edit_kind,
)

_sys.modules[__name__] = _importlib.import_module("drift_engine.fix_intent")
