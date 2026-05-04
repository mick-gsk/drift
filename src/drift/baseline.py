"""Re-export stub -- baseline implementation lives in drift_engine.baseline."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_engine.baseline import *

_sys.modules[__name__] = _importlib.import_module("drift_engine.baseline")
