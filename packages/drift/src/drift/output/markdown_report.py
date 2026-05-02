"""Re-export stub -- drift_output.markdown_report (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

from drift_output.markdown_report import analysis_to_markdown  # noqa: F401

_sys.modules[__name__] = _importlib.import_module("drift_output.markdown_report")
