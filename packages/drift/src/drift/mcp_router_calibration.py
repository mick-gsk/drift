"""Re-export stub -- drift_mcp.mcp_router_calibration (ADR-100 Phase 5a)."""

import importlib as _importlib
import sys as _sys

from drift_mcp.mcp_router_calibration import (
    run_calibrate as run_calibrate,
)
from drift_mcp.mcp_router_calibration import (  # noqa: F401
    run_feedback as run_feedback,
)

_sys.modules[__name__] = _importlib.import_module("drift_mcp.mcp_router_calibration")
