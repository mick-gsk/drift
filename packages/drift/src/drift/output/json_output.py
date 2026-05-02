"""Re-export stub -- drift_output.json_output (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

from drift_output.json_output import (  # noqa: F401
    _finding_to_dict,
    analysis_to_json,
    findings_to_sarif,
)

_sys.modules[__name__] = _importlib.import_module("drift_output.json_output")
