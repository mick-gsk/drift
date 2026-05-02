"""Re-export stub -- canonical implementation lives in drift_engine.signal_registry."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_engine.signal_registry import *

_sys.modules[__name__] = _importlib.import_module("drift_engine.signal_registry")
