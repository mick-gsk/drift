"""Re-export stub -- output package lives in drift_output (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

_sys.modules[__name__] = _importlib.import_module("drift_output")
