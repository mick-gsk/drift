"""Re-export stub -- canonical implementation lives in drift_output.recommendation_refiner."""
# ruff: noqa: F401, F403

import importlib as _importlib
import sys as _sys

from drift_output.recommendation_refiner import *

_sys.modules[__name__] = _importlib.import_module("drift_output.recommendation_refiner")
