"""Re-export stub -- drift_output.json_output (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys
from typing import Any

from drift_output.json_output import *  # noqa: F401,F403

analysis_to_json: Any
findings_to_sarif: Any
_finding_to_dict: Any

_sys.modules[__name__] = _importlib.import_module("drift_output.json_output")
