"""Re-export stub -- canonical implementation lives in drift_engine.response_shaping."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_engine.response_shaping import *

# Explicit re-exports for mypy (sys.modules aliasing is invisible to static analysis)
from drift_engine.response_shaping import (
    _ALWAYS_KEEP as _ALWAYS_KEEP,
)
from drift_engine.response_shaping import (
    _PROFILE_KEEP as _PROFILE_KEEP,
)
from drift_engine.response_shaping import (
    _base_response as _base_response,
)

_sys.modules[__name__] = _importlib.import_module("drift_engine.response_shaping")
