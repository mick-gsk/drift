"""Re-export stub -- canonical implementation lives in drift_engine.response_shaping."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_engine.response_shaping import *

_sys.modules[__name__] = _importlib.import_module("drift_engine.response_shaping")
