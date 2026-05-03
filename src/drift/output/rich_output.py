"""Re-export stub -- drift_output.rich_output (ADR-100 Phase 4a)."""

import importlib as _importlib
import sys as _sys
from typing import Any

from drift_output.rich_output import *  # noqa: F401,F403

render_feedback_calibration_hint: Any
render_findings: Any
render_full_report: Any
render_recommendations: Any
render_timeline: Any
render_trend_chart: Any
_read_code_snippet: Any

_sys.modules[__name__] = _importlib.import_module("drift_output.rich_output")
