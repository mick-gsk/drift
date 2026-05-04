"""Re-export stub -- drift_output.llm_output (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

from drift_output.llm_output import analysis_to_llm  # noqa: F401

_sys.modules[__name__] = _importlib.import_module("drift_output.llm_output")
