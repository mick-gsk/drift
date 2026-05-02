"""Re-export stub -- canonical implementation lives in drift_engine.adr_scanner."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_engine.adr_scanner import *

_sys.modules[__name__] = _importlib.import_module("drift_engine.adr_scanner")
