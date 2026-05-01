"""Re-export stub -- drift_output.session_renderer (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

from drift_output.session_renderer import render_session_report  # noqa: F401

_sys.modules[__name__] = _importlib.import_module("drift_output.session_renderer")
