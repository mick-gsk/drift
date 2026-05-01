"""Re-export stub -- drift_output.rich_output (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys

from drift_output.rich_output import (  # noqa: F401
    _read_code_snippet,
    render_feedback_calibration_hint,
    render_findings,
    render_full_report,
    render_recommendations,
    render_timeline,
    render_trend_chart,
)

_sys.modules[__name__] = _importlib.import_module("drift_output.rich_output")
