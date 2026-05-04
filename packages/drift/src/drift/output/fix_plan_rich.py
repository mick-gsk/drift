"""Re-export stub -- drift_output.fix_plan_rich (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

from drift_output.fix_plan_rich import render_fix_plan  # noqa: F401

_sys.modules[__name__] = _importlib.import_module("drift_output.fix_plan_rich")
