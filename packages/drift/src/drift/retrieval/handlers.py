"""Re-export stub -- retrieval implementation lives in drift_engine.retrieval (ADR-102 Phase A)."""

# ruff: noqa: F401, F403
import importlib as _importlib
import sys as _sys

from drift_engine.retrieval.handlers import *

_sys.modules[__name__] = _importlib.import_module("drift_engine.retrieval.handlers")
