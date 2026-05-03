"""Re-export stub -- drift_output.badge_svg (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

from drift_output.badge_svg import render_badge_svg  # noqa: F401

_sys.modules[__name__] = _importlib.import_module("drift_output.badge_svg")
