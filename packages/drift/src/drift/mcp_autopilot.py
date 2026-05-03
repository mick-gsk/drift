"""Re-export stub -- drift_mcp.mcp_autopilot (ADR-100 Phase 5a)."""

import importlib as _importlib
import sys as _sys

from drift_mcp.mcp_autopilot import (  # noqa: F401
    build_autopilot_summary as build_autopilot_summary,
)

_sys.modules[__name__] = _importlib.import_module("drift_mcp.mcp_autopilot")
