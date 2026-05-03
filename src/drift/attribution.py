"""Re-export stub -- canonical implementation lives in drift_sdk.attribution."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_sdk.attribution import *

_sys.modules[__name__] = _importlib.import_module("drift_sdk.attribution")
