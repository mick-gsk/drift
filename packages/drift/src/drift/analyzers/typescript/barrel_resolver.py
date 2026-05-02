# Re-export stub -- canonical implementation in drift_engine.analyzers.typescript.barrel_resolver (ADR-102 Phase B).
import importlib as _importlib
import sys as _sys

from drift_engine.analyzers.typescript.barrel_resolver import *  # noqa: F401,F403

_sys.modules[__name__] = _importlib.import_module("drift_engine.analyzers.typescript.barrel_resolver")
