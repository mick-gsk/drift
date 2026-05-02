"""Re-export stub -- drift_output.csv_output (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

from drift_output.csv_output import analysis_to_csv  # noqa: F401

_sys.modules[__name__] = _importlib.import_module("drift_output.csv_output")
